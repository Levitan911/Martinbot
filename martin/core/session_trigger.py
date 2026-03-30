import logging
from conf.settings import config
from martin.core.chat_merger import merge_chat_from_file_or_string

logger = logging.getLogger(__name__)

KEYWORD = config.martin.general.KEYWORD


def build_chat_history(df_record, sliding_window_size=config.martin.core.sliding_window_size):
    """
    构建聊天记录，将消息内容添加到新的列中
    
    Args:
        df_record: 聊天记录 DataFrame
    
    Returns:
        list: 聊天记录列表
    """
    try:
        df_record.fillna(value="", inplace=True)
    
        df_record['role_bubble_content'] = df_record['sender_nickname'] + "<" + \
            df_record['content_type'] + "消息>：" + df_record['text_content'] + df_record['raw_description']
        
        return df_record.tail(sliding_window_size+1)['role_bubble_content'].values.tolist()[:-1]
    except Exception as e:
        logger.error(f"构建会话历史失败：{e}")
        return []


def trigger_session(keyword, df_record, new_message_num):
    """
    触发会话：根据关键词从新消息中提取相关内容
    
    Args:
        keyword: 触发关键词
        df_record: 聊天记录 DataFrame
        new_message_num: 新消息数量
    
    Returns:
        包含关键词的消息列表，每个元素为格式化的字符串
    """
    session_cache = []
    
    if df_record is None or df_record.empty:
        logger.info("聊天记录为空")
        return session_cache
    
    if new_message_num < 0:
        logger.info("新消息数量无效")
        return session_cache
    
    # 获取最新的消息
    latest_record = df_record.tail(new_message_num)
    
    if latest_record.empty:
        logger.info("**没有新的消息**")
        return session_cache
    
    # 遍历最新消息，查找包含关键词的消息
    for idx, msg in zip(latest_record.index.values, latest_record['text_content'].values):
        if isinstance(msg, str):
            if keyword in msg:
                sender_name = latest_record.loc[idx]['sender_nickname']
                logger.info(f"{sender_name} 发送了包含 {keyword} 的消息: “{msg}”")
                query = f"{sender_name}对你说：{msg.replace(keyword, '').strip()}"
                session_cache.append((sender_name, query))
    
    return session_cache


def trigger_session_from_file_or_string(keyword=KEYWORD, chat_file_or_string="dialog_info/latest_chat_example.md", data_file="dialog_info/chat_data.csv"):
    """
    从文件加载聊天记录并触发会话
    
    Args:
        keyword: 触发关键词
        chat_file_or_string: 新聊天记录文件路径或字符串
        data_file: 聊天数据文件路径
    
    Returns:
        包含关键词的消息列表
    """
    # 合并新聊天记录
    df_record, new_message_num = merge_chat_from_file_or_string(chat_file_or_string, data_file)

    if df_record is None:
        logger.error("合并聊天记录失败")
        return []
    
    # 触发会话
    session_cache = trigger_session(keyword, df_record, new_message_num)
    if session_cache:
        return session_cache, build_chat_history(df_record)
    else:
        return session_cache, []


if __name__ == "__main__":
    # 示例使用
    print("会话触发器")
    print("=" * 50)
    
    # 从文件触发会话
    session_cache, chat_history = trigger_session_from_file_or_string()
    
    if session_cache:
        print(f"\n会话缓存:")
        print("=" * 50)
        for idx, query in enumerate(session_cache, 1):
            print(f"{idx}. {query}")
        print(f"\n聊天记录:")
        print("=" * 50)
        for idx, msg in enumerate(chat_history, 1):
            print(f"{idx}. {msg}")
    else:
        print("没有触发会话")
