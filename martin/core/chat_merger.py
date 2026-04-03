import os
import re
import pandas as pd
import logging
from pathlib import Path
from conf.settings import config
from martin.core.chat_parser import load_json, parse_chat_data
from martin.claw.send_message import send_message

logger = logging.getLogger(__name__)

DEFAULT_CHAT_DATA_FILE = config.martin.general.DEFAULT_CHAT_DATA_FILE
KEYWORD = config.martin.general.KEYWORD


def load_existing_chat_data(data_file=DEFAULT_CHAT_DATA_FILE):
    """
    加载现有的聊天记录数据
    
    Args:
        data_file: 数据文件路径
    
    Returns:
        DataFrame 对象，如果文件不存在返回空 DataFrame
    """
    if not os.path.exists(data_file):
        Path(data_file).parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"数据文件不存在，将创建新文件: {data_file}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(data_file, encoding='utf-8-sig')
        logger.info(f"已加载现有数据: {len(df)} 条消息")
        return df
    except Exception as e:
        logger.error(f"加载数据文件失败: {e}")
        return pd.DataFrame()


def merge_chat_data(existing_df, new_json_str, data_file=DEFAULT_CHAT_DATA_FILE, repetition_check_area=config.core.repetition_check_area):
    """
    将新的聊天记录合并到现有数据中
    
    Args:
        existing_df: 现有的 DataFrame
        new_json_str: 新的聊天记录 JSON 字符串
        data_file: 数据文件路径
        repetition_check_area: 重复检查区域，默认 9
    
    Returns:
        merged_df: 合并后的 DataFrame
        new_message_num: 新消息数
    """
    new_message_num = 0
    try:
        # 解析新的 JSON 数据
        new_data = load_json(new_json_str)
        new_df = parse_chat_data(new_data)
        
        if new_df.empty:
            logger.info("新数据为空，无需合并")
            merged_df = existing_df
        else:
            # 合并数据
            if existing_df.empty:
                merged_df = new_df
                new_message_num = len(new_df)
            else:
                # 移除重复消息
                # 创建布尔掩码：找出 new_df 中需要删除的行
                f = lambda x: re.sub(r'[\s!?！？]', '', x)[-8:] if isinstance(x, str) else x
                mask_text = new_df['text_content'].map(f).isin(existing_df['text_content'].tail(repetition_check_area).map(f))
                mask_raw = new_df['raw_description'].map(f).isin(existing_df['raw_description'].tail(repetition_check_area).map(f))

                # 合并条件：只要有一个字段重复就算重复 (逻辑或)
                mask_to_drop = mask_text | mask_raw

                # 直接过滤掉重复行
                new_df_cleaned = new_df[~mask_to_drop]  # ~ 代表取反
                if new_df_cleaned.empty:
                    logger.info("没有新的有效消息，无需合入")
                    merged_df = existing_df
                else:
                    merged_df = pd.concat([existing_df, new_df_cleaned], ignore_index=True)
                    merged_df['msg_id'] = merged_df.index.values + 1
                    new_message_num = len(new_df_cleaned)
            
            if new_message_num > 0:
                logger.info(f"新消息数: {new_message_num} 条")
                # 保存到文件
                merged_df.to_csv(data_file, index=False, encoding='utf-8-sig')
                logger.info(f"数据已保存到: {data_file}")
                logger.info(f"总消息数: {len(merged_df)}")
                
        return merged_df, new_message_num
    
    except Exception as e:
        logger.error(f"合并数据失败: {e}")
        msg = "我嘞个豆，看花眼了，你再试试呢！"
        logger.info(f"\n{KEYWORD[1:]}回复: {msg}")

        send_message(msg)
        return existing_df, 0


def merge_chat_from_file_or_string(input_path_or_content, data_file=DEFAULT_CHAT_DATA_FILE):
    """
    从文件加载新的聊天记录并合并到现有数据中
    
    Args:
        input_path_or_content: 新聊天记录文件路径或 JSON 字符串
        data_file: 数据文件路径
    
    Returns:
        合并后的 DataFrame
    """
    try:
        if '{' not in input_path_or_content:
            with open(input_path_or_content, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = input_path_or_content
        
        # 移除 markdown 代码块标记
        if content.strip().startswith("```json"):
            content = content.strip()
            content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        elif content.strip().startswith("```"):
            content = content.strip()
            content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        
        # 加载现有数据
        existing_df = load_existing_chat_data(data_file)
        
        # 合并数据
        return merge_chat_data(existing_df, content, data_file)
        
    except FileNotFoundError:
        logger.error(f"文件未找到: {new_json_file}")
        return None
    except Exception as e:
        logger.error(f"处理文件失败: {e}")
        return None


def get_chat_statistics(data_file=DEFAULT_CHAT_DATA_FILE):
    """
    获取聊天记录统计信息
    
    Args:
        data_file: 数据文件路径
    
    Returns:
        统计信息字典
    """
    df = load_existing_chat_data(data_file)
    
    if df.empty:
        return {
            "total_messages": 0,
            "participants": [],
            "message_types": [],
            "sender_stats": {}
        }
    
    return {
        "total_messages": len(df),
        "participants": df['sender_nickname'].unique().tolist(),
        "message_types": df['content_type'].unique().tolist(),
        "sender_stats": df['sender_nickname'].value_counts().to_dict()
    }


if __name__ == "__main__":
    print("聊天记录合并器")
    print("=" * 50)
    
    # 示例: 从文件合并
    print("\n示例: 从文件合并新聊天记录")
    print("-" * 50)
    df, _ = merge_chat_from_file("dialog_info/new_chat_example.md")
    
    if df is not None:
        # 显示统计信息
        stats = get_chat_statistics()
        print(f"\n统计信息:")
        print(f"  总消息数: {stats['total_messages']}")
        print(f"  参与者: {', '.join(stats['participants'])}")
        print(f"  消息类型: {', '.join(stats['message_types'])}")
        
        # 显示发送者统计
        print(f"\n发送者统计:")
        for name, count in stats['sender_stats'].items():
            print(f"  {name}: {count} 条")
