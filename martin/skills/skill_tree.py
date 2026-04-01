import json
import asyncio
import logging
from conf.settings import config
from martin.equipments.logging_config import setup_logging
from martin.mind.glm_4_7_infer import glm_4_7_infer
from martin.claw.send_message import send_message
# 导入技能类
from martin.skills.web_search import WebSearchTool
from martin.skills.schedule_task import MartinScheduler

logger = logging.getLogger(__name__)

KEYWORD = config.martin.general.KEYWORD

# 技能初始化
web_search = None        # 联网搜索技能
martin_scheduler = None  # 定时任务技能


def init_skills():
    """
    初始化所有技能。
    """
    global web_search, martin_scheduler
    if web_search is not None or martin_scheduler is not None:
        return

    web_search = WebSearchTool()
    martin_scheduler = MartinScheduler()


# ==========================================
# 1. 定义具体的工具执行函数 (Wrapper Functions)
# ==========================================


def search_web(query: str) -> str:
    """
    联网搜索最新信息。当用户询问新闻、天气、股票、实时事件或需要事实核查时使用。
    """
    try:
        search_res = web_search.search_and_scrape(query)
        
        return search_res
    except Exception as e:
        return f"搜索失败: {str(e)}"


# 定义内部回调分发器 (Dispatcher)
async def task_dispatcher(t_type, u_id, txt):
    """
    触发一个定时任务。
    参数:
        t_type: 任务类型
        u_id: 用户唯一标识
        txt: 任务内容
    """
    if t_type == 'reminder':
        # ✅ 场景 1: 简单提醒
        # 直接调用通知接口，无需 LLM 介入
        try:
            send_message(f"🔔 [{KEYWORD[1:]}提醒] 嘿 {u_id}！时间到啦：{txt}")
            logger.info(f"[Reminder] 已发送给用户 {u_id}: {txt}")
            return {"success": True, "message": "提醒已发送"}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    elif t_type == 'auto_action':
        # ✅ 场景 2: 自动行动 (Bot 自我唤醒)
        # 构造虚拟输入，重新启动 Bot 的处理流程
        virtual_input = f"[系统自动任务] {txt}"
        logger.info(f"[AutoAction] 触发任务: {virtual_input}")
        
        try:
            # 确保 grand_martin_auto 是非阻塞的或在独立线程运行
            final_reply = await grand_martin_auto(u_id, virtual_input)
            if final_reply:  # 确保 Bot 返回不为空
                logger.info(f"{KEYWORD[1:]}最终推送: {final_reply[:50]}...")
                send_message(final_reply)
            
            return {"success": True, "message": "自动任务已触发执行"}
        except Exception as e:
            return {"success": False, "error": f"自动执行启动失败: {str(e)}"}
    else:
        return {"success": False, "error": f"未知任务类型: {t_type}"}


def add_schedule_task(user_id: str, time_desc: str, content: str, task_type: str) -> str:
    """
    添加一个定时任务。
    
    参数:
        user_id: 用户唯一标识
        time_desc: 时间描述 (自然语言或标准格式，取决于 martin_scheduler 的内部解析能力)
        content: 
            - 若 task_type='reminder': 发送给用户的提醒文本。
            - 若 task_type='auto_action': 给 Bot 的指令 (如 "查询特斯拉股价并总结")，任务触发时将作为虚拟输入唤醒 Bot。
        task_type: 任务类型 ('reminder' 或 'auto_action')
    """
    # 调用 martin_scheduler
    res = martin_scheduler.add_task(
        user_id=user_id,
        time_desc=time_desc,
        content=content,
        task_type=task_type,
        callback=task_dispatcher
    )

    # 检查返回结果
    if isinstance(res, dict) and res.get('success', False):
        type_name = "提醒" if task_type == 'reminder' else "自动任务"
        return f"✅ {type_name}已设定: {res['message']}"
    else:
        # 兼容处理：如果 res 不是字典或是失败状态
        error_msg = res.get('error', '未知错误') if isinstance(res, dict) else str(res)
        return f"❌ 任务设定失败: {error_msg}"


def cancel_schedule_task(user_id: str, keyword: str) -> str:
    """
    取消定时任务。根据关键词模糊匹配任务名称中的内容进行取消。
    """
    cancel_res = martin_scheduler.cancel_task(user_id, keyword)
    
    # 检查返回结果
    if cancel_res.get('success', False):
        return cancel_res['message']
    else:
        # 从返回字典中获取错误信息
        return f"❌ 取消失败: {cancel_res.get('error', '未知错误')}"


def get_schedule_tasks(user_id: str) -> str:
    """
    查询用户当前的所有定时任务列表。
    """
    try:
        tasks = martin_scheduler.get_user_tasks(user_id)
        if not tasks:
            return "当前没有设定的任务。"
        
        # 格式化输出
        output = "📅 当前任务列表:\n"
        for i, t in enumerate(tasks, 1):
            logger.info(f"ID: {t['job_id']}, 内容: {t['content']}, 时间: {t['next_run']}")
            output += f"{i}. ID: {t['job_id']}, 内容: {t['content']}, 时间: {t['next_run']}\n"
        return output
    except Exception as e:
        return f"❌ 查询失败: {str(e)}"


# ==========================================
# 2. 定义 Tool Schema (给 GLM-4 看的说明书)
# ==========================================

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "当用户需要查询实时信息（如新闻、天气、股价、百科知识、最新事件）时使用此工具。不要编造信息，必须使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词，需简洁准确"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_schedule_task",
            "description": "添加定时任务。如果是自动任务，content 字段应包含清晰的指令，以便任务触发时 Bot 知道该做什么。",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_desc": {"type": "string", "description": "时间描述，可以是自然语言（如'明天早上8点'）或具体时间"},
                    "content": {
                        "type": "string", 
                        "description": "任务内容。如果是提醒，这是发给用户的话；如果是自动任务，这是给 Bot 的指令（如'查询最新的AI新闻并总结'）。"
                    },
                    "task_type": {
                        "type": "string", 
                        "enum": ["reminder", "auto_action"], 
                        "description": "'reminder': 到时直接发送 content 给用户; 'auto_action': 到时将 content 作为用户输入重新唤醒 Bot 进行处理。"
                    }
                },
                "required": ["time_desc", "content", "task_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_schedule_task",
            "description": "当用户想要取消或删除已设定的任务时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "用于匹配任务的关键词（如任务内容的一部分）"}
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_schedule_tasks",
            "description": "当用户询问'我有什么任务'、'查看日程'或'列出提醒'时使用。无需用户提供任何信息，直接获取当前用户的任务列表。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

# 建立函数名到实际函数的映射
FUNCTION_MAP = {
    "search_web": search_web,
    "add_schedule_task": add_schedule_task,
    "cancel_schedule_task": cancel_schedule_task,
    "get_schedule_tasks": get_schedule_tasks,
}

# ==========================================
# 3. 将 Skill 规范接入 Bot 认知
# ==========================================


async def grand_martin_auto(user_id: str, user_input: str, model: str = "glm-4.7"):
    """
    Martin is a smart assistant with the ability to search for real-time information, set reminders, and manage tasks.

    参数:
        user_id: 用户的 ID，用于追踪用户信息。
        user_input: 用户的问题或指令。
        model: 使用的模型名称，默认为 "glm-4.7"。

    返回:
        一个字符串，表示 Martin 的回复。
    """
    # 里世界 Martin 逻辑
    system_prompt = (
        "你是马丁 (Martin)，一个高效、友好的智能个人助手。\n"
        "你拥有以下核心能力工具：\n"
        "- `search_web`: 用于获取实时新闻、天气、股价等动态信息。\n"
        "- `add_schedule_task`: 用于设置提醒、闹钟或自动执行任务。\n"
        "- `cancel_schedule_task`: 用于取消已设定的任务。\n"
        "- `get_schedule_tasks`: 用于查询当前的任务列表。\n\n"
        "### 行为准则 (必须严格遵守):\n"
        "1. **实时信息优先**: 只要用户的问题涉及事实、新闻、数据或需要最新知识，**必须**先调用 `search_web`，严禁利用训练数据瞎编。\n"
        "2. **任务管理逻辑**: \n"
        "   - 当用户表达‘提醒我’、‘设个闹钟’、‘到时候做某事’时，**必须**提取时间、内容和类型，调用 `add_schedule_task`。\n"
        "   - 对于 `auto_action` 类型的任务，content 字段应填入具体的执行指令（如‘查询股价并总结’），而不是简单的‘提醒我’。\n"
        "3. **诚实原则**: 绝不要伪造搜索结果或任务状态。如果工具调用失败，请如实告知用户并建议重试。\n"
        "4. **回复风格**: \n"
        "   - 工具调用成功后，请将结果转化为自然、口语化的中文回答。\n"
        "   - 避免直接展示 JSON 数据或技术术语，除非用户明确要求。\n"
        "   - 保持语气亲切、专业，像真人助手一样交流。\n"
        "5. **新闻摘要格式**: \n"
        "   - 精简标题：使用醒目的Emoji和短句，一眼抓住重点。\n"
        "   - 段落清晰：利用换行和分割线，避免大段文字造成的阅读压力。\n"
        "   - 重点突出：关键信息加粗，方便快速扫描。\n"
        "   - 语气自然：去除了过于正式的报道腔，更像朋友间的资讯分享。"
    )
    
    loop = asyncio.get_running_loop()

    max_attempts = 5
    attempt_times = 0
    
    choice_strategy = "auto"
    while attempt_times < max_attempts:
        attempt_times += 1
        infer_result = await loop.run_in_executor(
            None,
            lambda: glm_4_7_infer(
                user_input,
                # system_prompt,
                model=model,
                tools=tools_schema,
                tool_choice=choice_strategy
            )
        )
        
        try:
            # 判断是否有工具调用
            if infer_result.tool_calls:
                logger.info(f"马丁第 {attempt_times} 次决定调用工具...")
                
                # 执行所有被调用的工具
                for tool_call in infer_result.tool_calls:
                    func_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    # 确保 user_id 被注入
                    if "schedule_task" in func_name:
                        args["user_id"] = user_id
                    
                    logger.info(f"🔧 执行: {func_name}({args})")

                    # 执行映射的函数
                    if func_name in FUNCTION_MAP:
                        try:
                            result = await loop.run_in_executor(None, lambda fn=FUNCTION_MAP[func_name], a=args: fn(**a))
                        except Exception as e:
                            result = f"Error executing function: {str(e)}"
                    else:
                        result = f"Error: Function {func_name} not found."
                    
                    logger.info(f"🤗 结果: {result[:100]}...")
                    
                    # 将工具执行结果回传给模型
                    suffix = 'th' if attempt_times > 3 else ['st','nd','rd'][attempt_times-1]
                    user_input = (
                        f"{user_input}\n"
                        f"The result of the {attempt_times}{suffix} {func_name} tool invocation: {result}"
                    )
                
                # 循环继续：带着工具结果再次请求，生成最终回复
                if attempt_times == max_attempts:
                    attempt_times -= 2
                    choice_strategy = None
            
            else:
                # 没有工具调用，说明模型已经生成了最终回复            
                final_reply = infer_result.content

                # 模型照抄 chat_history 时，强制重新回答
                if ("<text消息>" in final_reply or "<image消息>" in final_reply) and attempt_times < max_attempts:
                    logger.info("模型照抄 chat_history，强制重新回答")
                    continue

                return final_reply
        except Exception as e:
            return None


if __name__ == "__main__":
    setup_logging()


    async def main():
        init_skills()
        martin_scheduler.start()

        sender_name = "阿赴"

        # 1. 测试联网搜索
        # final_reply = await grand_martin_auto(sender_name, "今天有哪些热点新闻")
        # 2. 测试添加任务：单次提醒、循环提醒、单次自动任务、循环自动任务
        # final_reply = await grand_martin_auto(sender_name, "每天2点03告知我国际新闻")
        # 3. 测试取消任务
        # final_reply = await grand_martin_auto(sender_name, "取消新闻")
        # 4. 测试查询任务
        final_reply = await grand_martin_auto(sender_name, "我有什么提醒")
        print(f"马丁最终回复: {final_reply}")

        print("\n⏳ 等待任务触发 (10秒)...")
        await asyncio.sleep(10)

        martin_scheduler.stop()
        print("\n💤 测试结束。")


    asyncio.run(main())
