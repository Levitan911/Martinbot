import os
import re
import base64
import logging
from zai import ZhipuAiClient
from conf.settings import config

logger = logging.getLogger(__name__)

DEFAULT_API_KEY = config.martin.vision.DEFAULT_API_KEY
DEFAULT_SYSTEM_PROMPT_FILE = config.martin.vision.DEFAULT_SYSTEM_PROMPT_FILE
DEFAULT_USER_PROMPT_FILE = config.martin.vision.DEFAULT_USER_PROMPT_FILE
DEFAULT_MODEL = config.martin.vision.DEFAULT_MODEL


def encode_image_to_base64(img_path):
    """
    将图片文件编码为 base64
    
    Args:
        img_path: 图片文件路径
    
    Returns:
        base64 编码的字符串
    """
    with open(img_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def read_prompt_file(file_path):
    """
    读取提示词文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        文件内容字符串
    """
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def glm_4_6v_ocr(img_path, system_prompt=None, user_prompt=None, api_key=None, model=None):
    """
    使用 GLM-4.6V 模型进行 OCR 识别
    
    Args:
        img_path: 图片文件路径
        system_prompt: 系统提示词，默认从 dialog_info/system_prompt.txt 读取
        user_prompt: 用户提示词，默认从 dialog_info/user_prompt.md 读取
        api_key: API 密钥，默认使用内置密钥
        model: 模型名称，默认为 glm-4.6v-flash
    
    Returns:
        OCR 识别结果字符串
    """
    try:
        if api_key is None:
            api_key = DEFAULT_API_KEY
        
        if model is None:
            model = DEFAULT_MODEL
        
        client = ZhipuAiClient(api_key=api_key)
        
        img_base = encode_image_to_base64(img_path)
        
        if system_prompt is None:
            system_prompt = read_prompt_file(DEFAULT_SYSTEM_PROMPT_FILE)
        
        if user_prompt is None:
            user_prompt = read_prompt_file(DEFAULT_USER_PROMPT_FILE)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": img_base
                            }
                        },
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                }
            ],
            thinking={
                "type": "disabled"
            }
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"OCR 识别失败: {e}")
        
        pattern = r'"code"\s*:\s*"([^"]+)".*?"message"\s*:\s*"([^"]+)"'
        match = re.search(pattern, str(e), re.DOTALL)

        if match:
            code = match.group(1)
            message = match.group(2)
            return code, message
        
        return None


def glm_4_6v_ocr_with_files(img_path, system_prompt_file=None, user_prompt_file=None, api_key=None, model=None):
    """
    使用 GLM-4.6V 模型进行 OCR 识别（从文件读取提示词）
    
    Args:
        img_path: 图片文件路径
        system_prompt_file: 系统提示词文件路径
        user_prompt_file: 用户提示词文件路径
        api_key: API 密钥，默认使用内置密钥
        model: 模型名称，默认为 glm-4.6v-flash
    
    Returns:
        OCR 识别结果字符串
    """
    system_prompt = read_prompt_file(system_prompt_file) if system_prompt_file else None
    user_prompt = read_prompt_file(user_prompt_file) if user_prompt_file else None
    
    return glm_4_6v_ocr(img_path, system_prompt, user_prompt, api_key, model)


if __name__ == "__main__":
    img_path = "chat_screenshots/魏武遗风-3.png"
    result = glm_4_6v_ocr(img_path)
    
    if result:
        print(result)
    else:
        print("OCR 识别失败")
