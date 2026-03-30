import re
import logging
from datetime import datetime, timezone, timedelta
from zai import ZhipuAiClient
from zai.core import NOT_GIVEN
from conf.settings import config
from martin.vision.glm_4_6v_ocr import read_prompt_file
from martin.mind.extract_identity import get_today_martin
from martin.equipments.number_to_morse import number_to_morse
from martin.claw.send_message import send_message

logger = logging.getLogger(__name__)

DEFAULT_API_KEY = config.martin.mind.DEFAULT_API_KEY
DEFAULT_SYSTEM_PROMPT_TEMPLATE = config.martin.mind.DEFAULT_SYSTEM_PROMPT_TEMPLATE
DEFAULT_USER_PROMPT = "阿赴对你说：你觉得人生的意义是什么"
DEFAULT_MODEL = config.martin.mind.DEFAULT_MODEL
KEYWORD = config.martin.general.KEYWORD


def glm_4_7_infer(user_prompt, system_prompt=None, api_key=None, base_url=None, model=None, tools=NOT_GIVEN, tool_choice=NOT_GIVEN, max_tokens=65536, temperature=1.0):
    """
    使用 GLM-4.7 模型进行推理
    
    Args:
        user_prompt: 用户提示词
        system_prompt: 系统提示词，默认从文件读取
        api_key: API 密钥，默认使用内置密钥
        base_url: 基础 URL，默认使用内置 URL
        model: 模型名称，默认为 glm-4.7-flash
        tools: 工具列表，默认为 NOT_GIVEN
        tool_choice: 工具选择策略，默认为 NOT_GIVEN
        max_tokens: 最大 token 数，默认为 65536
        temperature: 温度参数，默认为 1.0
    
    Returns:
        模型回复内容，失败返回 None
    """
    try:
        if api_key is None:
            api_key = DEFAULT_API_KEY
        
        if model is None:
            model = DEFAULT_MODEL
        
        if system_prompt is None:
            system_prompt_template = read_prompt_file(DEFAULT_SYSTEM_PROMPT_TEMPLATE)
            martin = get_today_martin()
            current_bj_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
            system_prompt = system_prompt_template.format(
                identity_name=martin["身份名称"],
                identity_description=martin["特征描述"],
                fun_tip=martin["趣事提示"],
                current_bj_time=current_bj_time
            )
        
        client = ZhipuAiClient(api_key=api_key, base_url=base_url)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=tools,
            tool_choice=tool_choice,
            thinking={
                "type": "disabled",
            },
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message
    
    except Exception as e:
        logger.error(f"推理失败: {e}")

        pattern = r'"code"\s*:\s*"([^"]+)".*?"message"\s*:\s*"([^"]+)"'
        match = re.search(pattern, str(e), re.DOTALL)

        if match:
            code = match.group(1)
            message = match.group(2)

            msg = f"[摩尔斯传令官马丁]为您效劳，摩尔斯电码: {number_to_morse(code)}，包藏的信息为: {message}"
            logger.info(f"\n{KEYWORD[1:]}回复: {msg}")

            send_message(msg)
        return None


if __name__ == "__main__":
    # 示例使用
    print("GLM-4.7 推理机")
    print("=" * 50)
    
    # 示例: 基本推理
    print("\n示例: 基本推理")
    print("-" * 50)
    result = glm_4_7_infer(DEFAULT_USER_PROMPT)
    if result:
        print(f"回复: {result}")
