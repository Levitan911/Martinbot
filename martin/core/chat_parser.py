import json
import pandas as pd
import demjson3
import json_repair as jr
import logging
from conf.settings import config
from martin.equipments.fix_json_str import fix_json_quotes, fix_json_newlines, fix_json_syntax_errors

logger = logging.getLogger(__name__)

KEYWORD = config.martin.general.KEYWORD


def load_json(json_str):
    """
    解析 JSON 数据
    
    Args:
        json_str: JSON 数据字符串
    
    Returns:
        解析后的 JSON 数据
    """
    try:
        json_data = json.loads(json_str)
        return json_data
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析错误: {e}")
        try:
            json_str = fix_json_quotes(json_str)
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Load JSON Error P1: {e}")
            try:
                logger.info("Demjson3 尝试宽松解析中...")
                return demjson3.decode(json_str)
            except Exception as e:
                logger.error(f"Decode JSON Error P1: {e}")
                try:
                    json_str = fix_json_syntax_errors(json_str)
                    return demjson3.decode(json_str)
                except Exception as e:
                    logger.error(f"Decode JSON Error P2: {e}")
                    try:
                        json_str = fix_json_newlines(json_str)
                        return demjson3.decode(json_str)
                    except Exception as e:
                        logger.error(f"Decode JSON Error P3: {e}")
                        try:
                            logger.info("JSON-Repair 尽力补救中...")
                            return jr.loads(json_str)
                        except Exception as e:
                            logger.error(f"Load JSON Error P2: {e}")
                            logger.error(f"JSON String 修复失败，无效字符串↓ \n{json_str}")
                            return None
    except Exception as e:
        logger.error(f"Load JSON Error P3: {e}")
        logger.error(f"JSON String 修复失败，无效字符串↓ \n{json_str}")
        return None


def parse_chat_data(json_data):
    """
    解析聊天记录 JSON 数据
    
    Args:
        json_data: 聊天记录的 JSON 数据
    
    Returns:
        解析后的 DataFrame
    """
    messages = []
    metadata = json_data.get("metadata", {})
    
    for msg in json_data.get("messages", []):
        msg_id = msg.get("msg_id", "")
        timestamp = msg.get("timestamp", "")
        sender_info = msg.get("sender", {})
        content_info = msg.get("content", {})
        
        # 提取发送者信息
        sender_nickname = sender_info.get("nickname", "").replace("@", "")
        is_me = sender_info.get("is_me", False)
        side = sender_info.get("side", "")
        if side == "right":
            sender_nickname = KEYWORD.replace("@", "")
        
        # 提取内容信息
        content_type = content_info.get("type", "")
        text_content = content_info.get("text_content", "")
        raw_description = content_info.get("raw_description", "")
        
        messages.append({
            "msg_id": msg_id,
            "timestamp": timestamp,
            "sender_nickname": sender_nickname,
            "is_me": is_me,
            "side": side,
            "content_type": content_type,
            "text_content": text_content,
            "raw_description": raw_description,
            "chat_type": metadata.get("chat_type", ""),
            "extract_confidence": metadata.get("extract_confidence", 0.0),
            "screenshot_time": metadata.get("screenshot_time", ""),
            "participants": ", ".join(metadata.get("participants", []))
        })
    
    return pd.DataFrame(messages)


def save_chat_to_dataframe(json_str, output_file="dialog_info/chat_data.csv"):
    """
    将聊天记录 JSON 字符串保存为 DataFrame
    
    Args:
        json_str: 聊天记录的 JSON 字符串
        output_file: 输出文件名
    
    Returns:
        DataFrame 对象
    """
    try:
        # 解析 JSON
        json_data = load_json(json_str)
        
        # 转换为 DataFrame
        df = parse_chat_data(json_data)
        
        # 保存为 CSV
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"聊天记录已保存到: {output_file}")
        logger.info(f"共 {len(df)} 条消息")
        
        return df

    except Exception as e:
        logger.error(f"处理错误: {e}")
        return None


def load_chat(chat_record, output_file="dialog_info/chat_data.csv"):
    """
    加载聊天记录并转换为 DataFrame
    
    Args:
        chat_record: 聊天记录
        output_file: 输出文件名
    
    Returns:
        DataFrame 对象
    """
    try:
        # 判断输入类型
        if '{' not in chat_record:
            with open(chat_record, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = chat_record
        
        # 移除 markdown 代码块标记
        if content.strip().startswith("```json"):
            content = content.strip()
            content = content[7:]  # 移除 ```json
            if content.endswith("```"):
                content = content[:-3]  # 移除 ```
            content = content.strip()
        elif content.strip().startswith("```"):
            content = content.strip()
            content = content[3:]  # 移除 ```
            if content.endswith("```"):
                content = content[:-3]  # 移除 ```
            content = content.strip()
        
        return save_chat_to_dataframe(content, output_file)
        
    except FileNotFoundError:
        logger.error(f"文件未找到: {chat_record}")
        return None
    except Exception as e:
        logger.error(f"处理错误: {e}")
        return None


def display_chat_summary(df):
    """
    显示聊天记录摘要
    
    Args:
        df: 聊天记录的 DataFrame
    """
    if df is None or df.empty:
        print("没有聊天记录数据")
        return
    
    print("\n聊天记录摘要:")
    print("=" * 50)
    print(f"总消息数: {len(df)}")
    print(f"参与人数: {len(df['sender_nickname'].unique())}")
    print(f"消息类型: {', '.join(df['content_type'].unique())}")
    
    # 按发送者统计
    sender_counts = df['sender_nickname'].value_counts()
    print("\n发送者统计:")
    for name, count in sender_counts.items():
        print(f"  {name}: {count} 条")
    
    # 按消息类型统计
    type_counts = df['content_type'].value_counts()
    print("\n消息类型统计:")
    for msg_type, count in type_counts.items():
        print(f"  {msg_type}: {count} 条")


def filter_chat_data(df, sender=None, content_type=None, keyword=None):
    """
    过滤聊天记录
    
    Args:
        df: 聊天记录的 DataFrame
        sender: 发送者昵称
        content_type: 消息类型
        keyword: 关键词
    
    Returns:
        过滤后的 DataFrame
    """
    if df is None:
        return None
    
    filtered_df = df.copy()
    
    if sender:
        filtered_df = filtered_df[filtered_df['sender_nickname'] == sender]
    
    if content_type:
        filtered_df = filtered_df[filtered_df['content_type'] == content_type]
    
    if keyword:
        filtered_df = filtered_df[
            filtered_df['text_content'].str.contains(keyword, na=False) |
            filtered_df['raw_description'].str.contains(keyword, na=False)
        ]
    
    return filtered_df


if __name__ == "__main__":
    # 示例使用
    print("聊天记录分析仪")
    print("=" * 50)
    
    # 从文件加载
    df = load_chat("dialog_info/chat_example.md")
    
    if df is not None:
        # 显示摘要
        display_chat_summary(df)
        
        # 过滤示例
        text_messages = filter_chat_data(df, content_type="text")
        print(f"\n纯文本消息数: {len(text_messages)}")
        
        # 保存过滤结果
        text_messages.to_csv("dialog_info/text_messages.csv", index=False, encoding='utf-8-sig')
        print("纯文本消息已保存到: text_messages.csv")
