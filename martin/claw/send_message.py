import pyautogui
import pyperclip
import logging
from pathlib import Path
from conf.settings import config
from martin.equipments.capture_file import copy_files_to_clipboard
from martin.equipments.wechat_locator import show_saved_coordinates

logger = logging.getLogger(__name__)
pyautogui.PAUSE = 0.1


def send_message(reply, coordinates=None, click_count=config.martin.claw.click_count, click_interval=config.martin.claw.click_interval):
    """
    发送消息到微信
    
    Args:
        reply: 要发送的消息内容
        coordinates: 目标坐标列表 [(x1, y1), (x2, y2), ...]，默认使用最后一个坐标
        click_count: 点击次数，默认为 2
        click_interval: 点击间隔（秒），默认为 0.25
    
    Returns:
        成功返回 True，失败返回 False
    """
    try:
        # 获取目标坐标
        if coordinates is None:
            coordinates = show_saved_coordinates()
            if not coordinates:
                logger.error("无法获取坐标")
                return False
        
        target_x = coordinates[-1][0]
        target_y = coordinates[-1][1]
        logger.info(f"\n**目标坐标: ({target_x}, {target_y})**")
        
        if Path(reply).is_dir():
            copy_files_to_clipboard(reply)
            logger.info("1. 表情包已复制到剪贴板")
        else:
            # 步骤 1：将文本放入剪贴板
            pyperclip.copy(reply)
            logger.info("1. 文本已复制到剪贴板")
        
        # 步骤 2：指定位置并单击
        pyautogui.click(x=target_x, y=target_y, clicks=click_count, interval=click_interval)
        logger.info(f"2. 已点击坐标 ({target_x}, {target_y})")
        
        # 步骤 3：执行 Ctrl+V 粘贴
        pyautogui.hotkey('ctrl', 'v')
        logger.info("3. 已执行 Ctrl+V")
        
        # 步骤 4：执行 Enter 发送
        pyautogui.press('enter')
        logger.info("4. 已执行 Enter")
        
        logger.info("**消息发送成功**")
        return True
    
    except Exception as e:
        logger.error(f"\n消息发送失败: {e}")
        return False


if __name__ == "__main__":
    # 示例使用
    print("微信GUI自动化消息发送")
    print("=" * 50)
    
    # 示例消息
    reply = '''
"叮铃铃——"闹钟响了。

我迷迷糊糊地睁开眼，差点从床上弹起来——因为我的腿太长了！我低头一看，自己竟然穿着一身蓝色的泳裤，皮肤上全是橘黄色的条纹。妈妈叫道："早安，马丁！今天是什么天气？"

我抬头看了看窗外，今天是个大晴天！哈！太棒了！

"你好！今天早晨我变成了**大熊猫马丁**！"我憨厚地咧嘴一笑，露出了两颗标志性的大门牙。

虽然变成了大熊猫，但我还是那个马丁。我晃晃悠悠地走到镜子前，看着自己圆圆的大脑袋和黑白相间的毛皮，觉得挺酷的。能吃竹子不用写作业，简直是世界上最完美的变身！

罗娜正在楼下等我呢，她肯定又要开始吐槽我太胖了。郭莫还在睡觉，估计得等到上课铃响才会出现在教室门口。

所以，想和我聊天的话，就得快点了，不然我和罗娜的"熊猫游行"就要迟到了！
'''
    
    # 发送消息
    success = send_message(reply)
    
    if success:
        print("\n操作成功完成")
    else:
        print("\n操作失败")
