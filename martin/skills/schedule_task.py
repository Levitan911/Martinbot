import re
import json
import asyncio
import logging
from datetime import datetime
from typing import Callable, Optional, List, Dict, Any
from conf.settings import config
from martin.equipments.logging_config import setup_logging
from sqlalchemy import create_engine
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

logger = logging.getLogger(__name__)

# 数据库配置 (SQLite)
DB_URL = config.martin.skills.DB_URL
LLM = config.martin.general.LLM


class MartinScheduler:
    """
    里世界马丁的超级时间管理器 (基于 APScheduler)
    特性：持久化、异步非阻塞、支持模糊查询与取消
    """
    def __init__(self):
        # 1. 配置持久化 JobStore
        engine = create_engine(DB_URL, echo=False)
        jobstores = {
            'default': SQLAlchemyJobStore(url=DB_URL, engine=engine)
        }
        
        # 2. 初始化调度器
        self.scheduler = AsyncIOScheduler(jobstores=jobstores)
        
        # 3. 绑定事件监听 (可选：用于记录执行日志或错误报警)
        self.scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)
        
        self._started = False

    def start(self):
        """启动调度器 (应在 Bot 主程序启动时调用)"""
        if not self._started:
            self.scheduler.start()
            self._started = True
            logger.info("⏰ 里世界马丁时间管理器已启动，数据库连接正常。")
            
            # 打印当前加载的任务数
            jobs = self.scheduler.get_jobs()
            logger.info(f"📋 已从数据库恢复 {len(jobs)} 个待执行任务。")

    def stop(self):
        """停止调度器 (应在 Bot 关闭时调用)"""
        if self._started:
            self.scheduler.shutdown(wait=True)
            self._started = False
            logger.info("💤 里世界马丁时间管理器已休眠。")

    def _parse_time(self, time_desc: str) -> dict:
        """
        解析自然语言时间。
        支持：'10分钟后', '半小时后', '明天早上8点', '2026-03-18 10:00'
        """
        from martin.mind.glm_4_7_infer import glm_4_7_infer
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text = time_desc.strip().lower()
        
        # 通用解析 (处理绝对时间或 'tomorrow 8am')
        try:
            sys_prompt = f"""
            You are a time parsing assistant for a Python scheduler (APScheduler).
            Current Time: {now}

            Task: Analyze the user's time description and output a JSON object.
            Rules:
            1. Determine the type:
            - If the input describes a SINGLE specific point in time (e.g., "tomorrow", "next Friday", "in 5 minutes"), set "type": "once".
                - Required field: "datetime" (format: "YYYY-MM-DD HH:MM:SS").
            - If the input describes a RECURRING schedule (e.g., "every day", "every Monday", "hourly", "at 9am daily"), set "type": "recurring".
                - Required field: "cron_params" (a dictionary with keys like hour, minute, day_of_week, day, month, second). Use "*" or omit keys for "any".
                - Required field: "first_occurrence" (format: "YYYY-MM-DD HH:MM:SS", the next valid run time).

            2. Output ONLY valid JSON. No markdown, no explanations.

            Examples:

            User: "明天早上8点"
            Output: {{"type": "once", "datetime": "2026-03-19 08:00:00"}}

            User: "后天晚上9点"
            Output: {{"type": "once", "datetime": "2026-03-20 21:00:00"}}

            User: "每天下午5点"
            Output: {{"type": "recurring", "cron_params": {{"hour": 17, "minute": 0, "second": 0}}, "first_occurrence": "2026-03-19 17:00:00"}}

            User: "每周一上午9点半"
            Output: {{"type": "recurring", "cron_params": {{"hour": 9, "minute": 30, "second": 0, "day_of_week": "mon"}}, "first_occurrence": "2026-03-23 09:30:00"}}

            User: "每小时整点"
            Output: {{"type": "recurring", "cron_params": {{"minute": 0, "second": 0}}, "first_occurrence": "2026-03-18 21:00:00"}}

            User: "每月1号中午12点"
            Output: {{"type": "recurring", "cron_params": {{"hour": 12, "minute": 0, "second": 0, "day": 1}}, "first_occurrence": "2026-04-01 12:00:00"}}
            """
            try:
                time_zone = glm_4_7_infer(text, sys_prompt, model=LLM).content

                time_zone = re.sub(r'^```json\s*', '', time_zone.strip())
                time_zone = re.sub(r'\s*```$', '', time_zone)
                
                time_parsed = json.loads(time_zone)
                logger.info(f"Martin 解析时间: {text} -> {time_parsed}")

                return time_parsed
            except json.JSONDecodeError as e:
                raise ValueError(f"LLM 返回了无效的 JSON: {time_zone}") from e
        except Exception as e:
            raise ValueError(f"马丁无法理解这个时间 '{time_desc}': {str(e)}")

    def add_task(
        self,
        user_id: str,
        time_desc: str,
        content: str,
        task_type: str,
        callback: Callable
    ) -> Dict[str, Any]:
        """
        添加定时任务
        :return: {'success': bool, 'job_id': str, 'trigger_time': str, 'message': str}
        """
        try:
            time_parsed = self._parse_time(time_desc)

            job_type = time_parsed.get("type")

            if job_type == "once":
                # --- 处理单次任务 (Once) ---
                dt_str = time_parsed.get("datetime")
                if not dt_str:
                    raise ValueError("Type 'once' requires 'datetime' field")

                run_time = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            
                # 生成唯一且可读的 Job ID: user_timestamp_hash
                # 这样方便后续通过 user_id 查找
                job_id = f"{user_id}_{int(run_time.timestamp())}_{abs(hash(content)) % 10000}"
            
                self.scheduler.add_job(
                    func=callback,
                    trigger="date",
                    run_date=run_time,
                    args=[task_type, user_id, content],
                    id=job_id,
                    name=f"{user_id}|{content}",  # 将内容存入 name 字段，方便模糊搜索
                    replace_existing=True,        # 如果ID冲突则覆盖
                    misfire_grace_time=None,      # 错过执行时间不立即执行，视业务需求可调整
                    max_instances=1               # 最大实例数 1，同一任务排队
                )
                
                logger.info(f"✅ 任务已设定: [{job_id}] 于 {run_time} 执行")
                
                return {
                    "success": True,
                    "job_id": job_id,
                    "trigger_time": run_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "message": f"在日历上标记 {run_time.strftime('%m月%d日 %H:%M')} {content}"
                }

            elif job_type == "recurring":
                # --- 处理循环任务 (Recurring) ---
                cron_params = time_parsed.get("cron_params")
                first_occ = time_parsed.get("first_occurrence")
                if not cron_params:
                    raise ValueError("Type 'recurring' requires 'cron_params' field")

                first_occ_dt = datetime.strptime(first_occ, "%Y-%m-%d %H:%M:%S")

                job_id = f"{user_id}_{int(first_occ_dt.timestamp())}_{abs(hash(content)) % 10000}"
                
                # 动态解包参数字典
                self.scheduler.add_job(
                    func=callback,
                    trigger='cron',
                    args=[task_type, user_id, content],
                    id=job_id,
                    name=f"{user_id}|{content}",
                    replace_existing=True,
                    misfire_grace_time=None,
                    max_instances=1,
                    **cron_params
                )

                logger.info(f"✅ 循环任务已设定: [{job_id}] 于 {first_occ_dt} 首次执行")
                
                return {
                    "success": True,
                    "job_id": job_id,
                    "trigger_time": first_occ_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "message": f"在日历上标记 {first_occ_dt.strftime('%m月%d日 %H:%M')} {content}"
                }
                
            else:
                raise ValueError("Invalid job type. Expected 'once' or 'recurring'")

        except Exception as e:
            logger.error(f"❌ 任务设定失败: {e}")
            return {"success": False, "error": str(e)}

    def cancel_task(
        self, 
        user_id: str, 
        keyword: Optional[str] = None, 
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        取消任务
        模式 A: 精准取消 (提供 job_id)
        模式 B: 模糊取消 (提供 keyword，匹配任务名称中的内容)
        """
        removed_count = 0
        removed_ids = []

        try:
            if job_id:
                # 精准模式
                try:
                    self.scheduler.remove_job(job_id)
                    removed_count = 1
                    removed_ids.append(job_id)
                    logger.info(f"🚫 任务已取消: {job_id}")
                except Exception:
                    return {"success": False, "error": "未找到该任务或任务已执行"}

            elif keyword:
                # 模糊模式：遍历该用户的所有任务
                jobs = self.scheduler.get_jobs()
                prefix = f"{user_id}|"

                for job in jobs:
                    # 检查是否属于该用户 且 名称中包含关键词
                    if job.name and job.name.startswith(prefix) and keyword in job.name:
                        try:
                            self.scheduler.remove_job(job.id)
                            removed_count += 1
                            removed_ids.append(job.id)
                            logger.info(f"🚫 模糊匹配取消任务: {job.id} ({job.name})")
                        except Exception:
                            continue

                if removed_count == 0:
                    return {"success": True, "canceled_count": 0, "message": "没找到匹配的待办事项哦"}

            else:
                return {"success": False, "error": "必须提供任务ID或关键词"}

            return {
                "success": True,
                "canceled_count": removed_count,
                "canceled_ids": removed_ids,
                "message": f"成功取消了 {removed_count} 个任务"
            }

        except Exception as e:
            logger.error(f"❌ 取消任务失败: {e}")
            return {"success": False, "error": str(e)}

    def get_user_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户所有待执行任务 (用于让用户确认或马丁主动汇报)"""
        jobs = self.scheduler.get_jobs()
        prefix = f"{user_id}|"
        result = []
        
        for job in jobs:
            if job.name and job.name.startswith(prefix):
                # 解析 name: "user_id|content"
                parts = job.name.split('|', 1)
                content = parts[1] if len(parts) > 1 else "未知任务"
                
                result.append({
                    "job_id": job.id,
                    "content": content,
                    "next_run": job.next_run_time.strftime("%Y-%m-%d %H:%M") if job.next_run_time else "未知",
                    "trigger": str(job.trigger)
                })
        
        # 按时间排序
        result.sort(key=lambda x: x['next_run'])
        return result

    # --- 内部回调监听 ---
    def _on_job_executed(self, event):
        logger.info(f"⏰ 任务执行完毕: {event.job_id}")

    def _on_job_error(self, event):
        logger.error(f"⚠️ 任务执行出错: {event.job_id}, 异常: {event.exception}")


if __name__ == "__main__":
    martin_scheduler = MartinScheduler()


    async def mock_callback(uid, msg):
        print(f"\n🔔 [马丁提醒] 嘿 {uid}！时间到啦：{msg}")


    async def main_test():
        # 1. 启动
        martin_scheduler.start()
        
        user = "test_user_007"
        
        # 2. 添加任务
        print("\n--- 添加任务 ---")
        # res1 = martin_scheduler.add_task(user, "1分钟后", "喝水休息", mock_callback)
        res2 = martin_scheduler.add_task(user, "10秒后", "站起来伸懒腰", mock_callback)
        res3 = martin_scheduler.add_task(user, "每天晚上10点", "早睡", mock_callback)
        
        # print(res1['message'])
        print(res2['message'])
        print(res3['message'])
        
        # 3. 查看任务
        print("\n--- 当前待办列表 ---")
        tasks = martin_scheduler.get_user_tasks(user)
        for t in tasks:
            print(f"ID: {t['job_id']}, 内容: {t['content']}, 时间: {t['next_run']}")
        
        # 4. 模糊取消 (取消包含"早睡"的任务)
        print("\n--- 取消包含'早睡'的任务 ---")
        cancel_res = martin_scheduler.cancel_task(user, keyword="早睡")
        print(cancel_res['message'])
        
        # 5. 再次查看
        print("\n--- 剩余待办列表 ---")
        tasks = martin_scheduler.get_user_tasks(user)
        for t in tasks:
            print(f"ID: {t['job_id']}, 内容: {t['content']}, 时间: {t['next_run']}")

        # 6. 等待观察 (只等20秒，不会等到明天的任务)
        print("\n⏳ 等待任务触发 (20秒)...")
        await asyncio.sleep(20)
        
        # 7. 停止
        martin_scheduler.stop()
        print("\n💤 测试结束。")


    # 运行测试
    setup_logging()
    asyncio.run(main_test())
