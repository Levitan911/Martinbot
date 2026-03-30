import re
import logging

logger = logging.getLogger(__name__)


def fix_json_quotes(input_path_or_content):
    """
    修复 JSON 文件中的引号
    
    Args:
        input_path_or_content: 文件路径或文件内容
    """
    try:
        if '{' not in input_path_or_content:
            with open(input_path_or_content, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = input_path_or_content
            content_ls = content.split('\n')
            for idx, element in enumerate(content_ls):
                if element.count('"') > 4:
                    logger.info(f"element-{idx} 包含双引号，剔除中...")
                    head, sep, tail = element.partition(': "')
                    content_ls[idx] = head + sep + tail[:-2].replace('"', '') + '",'
            content = '\n'.join(content_ls)
            return content 
    except Exception as e:
        logger.error(f"修复失败: {e}")


def fix_json_newlines(json_str):
    def replace_inside_quotes(match):
        content = match.group(0)
        return content.replace('\n', '\\n').replace('\r', '\\r')

    robust_pattern = r'"(?:\\.|[^"\\\n\r]|[\n\r])*"'
    logger.info("U+000A 转义中...")
    
    return re.sub(robust_pattern, replace_inside_quotes, json_str)


def fix_json_syntax_errors(json_str):
    logger.info("JSON 语法错误修复中...")
    json_str = re.sub(r'(]\s*),"\s*,', r'\1,', json_str)
    json_str = re.sub(r'(}\s*),"\s*,', r'\1,', json_str)
    
    return json_str


def robust_fix_json(dirty_json_str):
    print("🚀 开始全能修复...")
    
    # --- 阶段 1: 修复结构层面的错误 (Structure Level) ---
    # 目标：把结构中错误的字面量 \n 变成真实换行，并去除多余符号
    # 注意：这里只处理出现在 ] 或 } 后面的情况，避免误伤字符串内部
    
    # 1.1 去除多余的引号和逗号组合: ],",  -> ],
    # 匹配: ] + 可选空格 + "," + 可选空格 + (字面量 \n 或 真实换行)
    dirty_json_str = re.sub(r'(]\s*),"\s*(?:\\n|\n)', r'\1,\n', dirty_json_str)
    dirty_json_str = re.sub(r'(}\s*),"\s*(?:\\n|\n)', r'\1,\n', dirty_json_str)
    
    # 1.2 修复结构中残留的字面量 \n (没有多余引号的情况): ],\n -> ],(真实换行)
    # 这里的 \\n 代表字面量的两个字符 \ 和 n
    dirty_json_str = re.sub(r'(]\s*),\s*\\n\s*', r'\1,\n', dirty_json_str)
    dirty_json_str = re.sub(r'(}\s*),\s*\\n\s*', r'\1,\n', dirty_json_str)
    dirty_json_str = re.sub(r'(]\s*)\\n\s*', r'\1\n', dirty_json_str)
    dirty_json_str = re.sub(r'(}\s*)\\n\s*', r'\1\n', dirty_json_str)

    # --- 阶段 2: 修复字符串内部的错误 (String Content Level) ---
    # 目标：把双引号内部的真实换行符变成转义序列 \n
    
    def escape_inside_quotes(match):
        content = match.group(0)
        # 将真实换行 (\n, \r) 替换为字面量 \\n, \\r
        # 此时结构已经干净，不用担心误伤结构
        return content.replace('\n', '\\n').replace('\r', '\\r')

    # 正则：匹配双引号包裹的内容，允许内部包含真实换行（以便我们能捕获并修复它）
    pattern = r'"(?:\\.|[^"\\\n\r]|[\n\r])*"'
    fixed_json_str = re.sub(pattern, escape_inside_quotes, dirty_json_str)
    
    return fixed_json_str


if __name__ == "__main__":
    fix_json_quotes("dialog_info/chat_example.md")
