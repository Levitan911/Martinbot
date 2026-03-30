

def number_to_morse(number_str):
    # 定义数字映射字典
    morse_dict = {
        '0': '-----',
        '1': '.----',
        '2': '..---',
        '3': '...--',
        '4': '....-',
        '5': '.....',
        '6': '-....',
        '7': '--...',
        '8': '---..',
        '9': '----.'
    }
    
    result = []
    for char in number_str:
        if char in morse_dict:
            result.append(morse_dict[char])
        else:
            # 如果遇到非数字字符，可以选择跳过或保留
            result.append('?') 
    
    # 用空格连接每个数字的编码
    return ' '.join(result)


if __name__ == "__main__":
    # 测试示例
    input_num = "2026"  # 比如今年是2026年
    output = number_to_morse(input_num)

    print(f"数字: {input_num}")
    print(f"摩尔斯码: {output}")
    # 预期输出: ..--- ----- ..--- -....
