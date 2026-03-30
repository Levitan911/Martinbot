## 输入数据
- **类型**：微信聊天窗口截图
- **方向判定**：左侧气泡 = 对方发送；右侧气泡 = 自己（或截图持有者）发送
- **可见元素**：头像、昵称、时间戳、消息气泡、输入框、状态栏（可选）

## 输出规范（JSON Schema）
{
  "metadata": {
    "screenshot_time": "string, 截图显示的时间（如状态栏有时间）",
    "participants": ["array, 识别到的所有发送者昵称"],
    "chat_type": "私聊|群聊|公众号", 
    "extract_confidence": "number, 0-1, 整体置信度"
  },
  "messages": [
    {
      "msg_id": "string, msg_序号",
      "timestamp": "string, 消息时间（HH:MM 或 YYYY-MM-DD HH:MM）",
      "sender": {
        "nickname": "string, 微信昵称",
        "is_me": "boolean, 是否为截图持有者",
        "side": "left|right"
      },
      "content": {
        "type": "text|image|emoji|voice|video|file|transfer|redpacket|system|card|link|miniapp",
        "text_content": "string, 文本内容（只有文字时）或图片描述",
        "raw_description": "string, 对非文本内容的详细描述（如：200元转账，备注'饭钱'；或语音时长12秒）"
      }
    }
  ]
}