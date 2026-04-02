import os
import art
import multiprocessing as mp
import asyncio
import logging

from termcolor import colored
from conf.settings import config
from concurrent.futures import ThreadPoolExecutor
from martin.skills import skill_tree
from martin.equipments.logging_config import setup_logging
from martin.vision.screen_monitor import screen_monitor
from martin.vision.glm_4_6v_ocr import glm_4_6v_ocr
from martin.core.session_trigger import trigger_session_from_file_or_string
from martin.claw.send_message import send_message

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = config.martin.general.SCREENSHOTS_DIR
BASE_IMAGE = config.martin.general.BASE_IMAGE
CHECK_INTERVAL = config.martin.general.CHECK_INTERVAL
DEFAULT_CHAT_DATA_FILE = config.martin.general.DEFAULT_CHAT_DATA_FILE
KEYWORD = config.martin.general.KEYWORD
USER_PROMPT_TEMPLATE = config.martin.general.USER_PROMPT_TEMPLATE
LLM = config.martin.general.LLM
STICKERS_DIR = config.martin.general.STICKERS_DIR

# 全局主事件循环
main_event_loop = None
executor = ThreadPoolExecutor(max_workers=1)


def get_screenshot_files():
    """
    获取截图目录中的所有图片文件
    
    Returns:
        图片文件名列表（排除 base_image）
    """
    if not os.path.exists(SCREENSHOTS_DIR):
        logger.error(f"截图目录不存在: {SCREENSHOTS_DIR}")
        return []
    
    files = os.listdir(SCREENSHOTS_DIR)
    # 过滤出图片文件，排除 base_image
    image_files = [
        f for f in files 
        if f.endswith(('.png', '.jpg', '.jpeg', '.bmp')) 
        and f != BASE_IMAGE
    ]
    
    return sorted(image_files)


def process_batch_sync():
    """同步业务逻辑"""
    screenshot_files = get_screenshot_files()
    
    if not screenshot_files:
        return
    
    logger.info(f"\n[Chat-Processor] 发现 {len(screenshot_files)} 个待处理截图")
    logger.info("=" * 50)
    
    success_count = 0
    
    for idx, image_file in enumerate(screenshot_files, 1):
        image_path = os.path.join(SCREENSHOTS_DIR, image_file)
        logger.info(f"[Chat-Processor] [{idx}/{len(screenshot_files)}] 处理: {image_file}")
        
        # 调用 OCR 识别
        ocr_result = glm_4_6v_ocr(image_path)
        
        if isinstance(ocr_result, str):
            logger.info(f"[Chat-Processor] 识别成功: {len(ocr_result)} 字符")
            success_count += 1

            session_cache, chat_history = trigger_session_from_file_or_string(keyword=KEYWORD, chat_file_or_string=ocr_result, data_file=DEFAULT_CHAT_DATA_FILE)
            
            if session_cache:
                logger.info(f"\n会话缓存:")
                logger.info("=" * 50)
                for idx, query in enumerate(session_cache, 1):
                    logger.info(f"{idx}. {query}")
                logger.info(f"\n聊天记录:")
                logger.info("=" * 50)
                for idx, msg in enumerate(chat_history, 1):
                    logger.info(f"{idx}. {msg}")

                chat_history = chr(10).join(chat_history)
                for sender_name, query in session_cache:
                    user_prompt = USER_PROMPT_TEMPLATE.format(chat_history=chat_history, query=query)

                    coro = skill_tree.grand_martin_auto(sender_name, user_prompt, model=LLM)
                    future = asyncio.run_coroutine_threadsafe(coro, main_event_loop)
                    final_reply = future.result()
                    
                    if final_reply:
                        prefix = "@" + sender_name + " "
                        if prefix not in final_reply:
                            msg = prefix + final_reply
                        else:
                            msg = final_reply
                        msg = msg.replace(KEYWORD, "")  # 增加容错
                        logger.info(f"\n{KEYWORD[1:]}回复: {msg}")

                        logger.info("\n微信GUI自动化消息发送")
                        logger.info("=" * 50)
                        success = send_message(msg)

                        if success:
                            logger.info("\n操作成功完成")
                        else:
                            logger.error("\n操作失败")
                    else:
                        logger.error("\n推理结果为 None")
            else:
                logger.info("\n没有触发会话")

            # 删除已处理的图片
            try:
                os.remove(image_path)
                logger.info(f"[Chat-Processor] 已删除: {image_file}")
            except Exception as e:
                logger.error(f"[Chat-Processor] 删除失败: {e}")
        else:
            logger.error(f"[Chat-Processor] 识别失败: {image_file}")
            
            if isinstance(ocr_result, tuple):
                code, msg = ocr_result

                if code == "1301":
                    msg = msg.replace("系统检测到输入或生成", "我发现输入").replace("您", "你")
                    logger.info(f"\n{KEYWORD[1:]}回复: {msg}")
                    success_count += 1
                    
                    send_message(msg)
                    send_message(STICKERS_DIR)
                    os.remove(image_path)
                    logger.info(f"\n[Chat-Processor] 已删除: {image_file}")
    
    logger.info(f"[Chat-Processor] 处理完成: 成功 {success_count}/{len(screenshot_files)}")
        

async def main_loop():
    """异步主循环"""
    skill_tree.martin_scheduler.start()
    
    while True:
        try:
            await asyncio.get_event_loop().run_in_executor(executor, process_batch_sync)
            await asyncio.sleep(CHECK_INTERVAL)
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"\n[Chat-Processor] 异常: {e}")
            await asyncio.sleep(5)


def process_executor():
    """
    Chat-Processor：处理图文按需应答（独立进程）
    
    Returns:
        处理成功的图片数量
    """
    setup_logging()
    logger.info("\n[Chat-Processor] 启动...")

    global main_event_loop

    loop = asyncio.new_event_loop()
    main_event_loop = loop
    asyncio.set_event_loop(loop)

    skill_tree.init_skills()

    try:
        loop.run_until_complete(main_loop())
    except KeyboardInterrupt:
        logger.info("\n\n[Chat-Processor] 已停止")
        skill_tree.martin_scheduler.stop()
        executor.shutdown(wait=True)
        loop.close()


def monitor_executor():
    """
    Screen-Monitor：持续监控屏幕变化（独立进程）
    """
    setup_logging()
    logger.info("\n[Screen-Monitor] 启动...")
    
    try:
        screen_monitor()
    except KeyboardInterrupt:
        logger.info("\n\n[Screen-Monitor] 已停止")
    except Exception as e:
        logger.error(f"\n[Screen-Monitor] 异常: {e}")


def main():
    """
    主函数：启动两个并行 executor
    """
    print(colored(art.text2art("Martinbot", font='tarty1'), "cyan"))
    print(colored(art.text2art("By Gabriel Gao", font='handwriting1'), "magenta"))

    logger.info("\noo聊天泡泡批处理oo（并行模式）")
    logger.info("=" * 50)
    logger.info(f"截图目录: {SCREENSHOTS_DIR}")
    logger.info(f"检查间隔: {CHECK_INTERVAL} 秒")
    logger.info("=" * 50)
    
    # 确保截图目录存在
    if not os.path.exists(SCREENSHOTS_DIR):
        os.makedirs(SCREENSHOTS_DIR)
        logger.info(f"已创建截图目录: {SCREENSHOTS_DIR}")
    
    try:
        # 创建两个进程
        proc_sm = mp.Process(target=monitor_executor, name="Screen-Monitor")
        proc_cp = mp.Process(target=process_executor, name="Chat-Processor")
        
        # 启动进程
        proc_sm.start()
        proc_cp.start()
        
        logger.info("\n两个 executor 已启动:")
        logger.info("  - [Screen-Monitor]: 持续监控屏幕变化")
        logger.info("  - [Chat-Processor]: 处理图文按需应答")
        logger.info("\n按 Ctrl+C 停止所有 executor\n")
        
        # 等待进程结束
        proc_sm.join()
        proc_cp.join()
        
        logger.info("\n所有 executor 已停止")
    
    except KeyboardInterrupt:
        logger.info("\n\n正在停止所有 executor...")
        
        # 终止进程
        if proc_sm.is_alive():
            proc_sm.terminate()
            proc_sm.join()
        
        if proc_cp.is_alive():
            proc_cp.terminate()
            proc_cp.join()
        
        logger.info("所有 executor 已停止")
    
    except Exception as e:
        logger.error(f"\n程序异常: {e}")


if __name__ == "__main__":
    setup_logging()
    main()
