import os
import sys
import time
import json
import pyautogui
import logging
from datetime import datetime
from pathlib import Path


def find_project_root(current_file: str, target_package: str = "martin") -> str:
    current_path = Path(current_file).resolve()

    for parent in [current_path.parent] + list(current_path.parents):
        if (parent / target_package).is_dir():
            return str(parent)
            
    raise FileNotFoundError(
        f"无法找到项目根目录：未在任意父目录中发现 '{target_package}' 文件夹。"
        f"当前搜索起点: {current_path}"
    )


if __name__ == "__main__":
    try:
        for module in ["conf", "martin"]:
            root_dir = find_project_root(__file__, module)
            
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
            
    except FileNotFoundError as e:
            print(f"[Error] {e}", file=sys.stderr)
            sys.exit(1)

from conf.settings import config
from martin.equipments.logging_config import setup_logging

logger = logging.getLogger(__name__)
pyautogui.PAUSE = 0.5

COORDINATES_FILE = config.martin.equipments.COORDINATES_FILE


def save_coordinate(x, y, button="left"):
    """
    保存鼠标坐标到本地文件
    
    Args:
        x: X坐标
        y: Y坐标
        button: 鼠标按钮 (left/right/middle)
    """
    coordinates = []
    if os.path.exists(COORDINATES_FILE):
        with open(COORDINATES_FILE, 'r', encoding='utf-8') as f:
            coordinates.extend(json.load(f))
    
    coordinate_data = {
        "x": x,
        "y": y,
        "button": button,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    coordinates.append(coordinate_data)
    
    with open(COORDINATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(coordinates, f, ensure_ascii=False, indent=2)
    
    logger.info(f"坐标已保存: X={x}, Y={y} ({button})")


def listen_and_save_clicks():
    """
    监听鼠标点击并保存坐标
    """
    try:
        from pynput import mouse
    except ImportError:
        logger.error("需要安装 pynput 库")
        logger.error("请运行: pip install pynput")
        return
    
    logger.info("鼠标点击监听已启动")
    logger.info("=" * 50)
    logger.info("点击鼠标左键/右键/中键将自动保存坐标")
    logger.info("按 Ctrl+C 停止监听")
    logger.info("=" * 50)
    click_count = 0
    logger.info("首次请点击【微信会话显示区左上角↖】")

    def on_click(x, y, button, pressed):
        nonlocal click_count

        if pressed:
            click_count += 1

            button_name = str(button).split('.')[-1]
            save_coordinate(int(x), int(y), button_name)

            if click_count == 1:
                logger.info("\n再则请点击【微信会话显示区右下角↘】")
            elif click_count == 2:
                logger.info("\n最后请点击【微信聊天输入区Ⅰ 】")
            else:
                logger.info("\n已记录3次点击，停止监听...")
                return False
    
    listener = mouse.Listener(on_click=on_click)
    
    try:
        listener.start()
        while listener.is_alive():
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.info("\n\n监听已停止")
        listener.stop()


def show_saved_coordinates():
    """
    显示已保存的坐标
    """
    if not os.path.exists(COORDINATES_FILE):
        logger.info("暂无保存的坐标")
        return
    
    try:
        with open(COORDINATES_FILE, 'r', encoding='utf-8') as f:
            coordinates = json.load(f)
        
        if not coordinates:
            logger.info("暂无保存的坐标")
            return
        
        logger.info(f"\n已保存的坐标 (共 {len(coordinates)} 条):")
        logger.info("=" * 50)
        
        for idx, coord in enumerate(coordinates, 1):
            logger.info(f"{idx}. X={coord['x']}, Y={coord['y']}, 按钮={coord['button']}, 时间={coord['timestamp']}")
        return [(coord['x'], coord['y']) for coord in coordinates]
    except (json.JSONDecodeError, FileNotFoundError):
        logger.error("读取坐标文件失败")


def clear_coordinates():
    """
    清空已保存的坐标
    """
    if os.path.exists(COORDINATES_FILE):
        os.remove(COORDINATES_FILE)
        logger.info("已清空所有保存的坐标")
    else:
        logger.info("暂无保存的坐标")


if __name__ == "__main__":
    setup_logging()
    logger.info("鼠标点击坐标记录程式")
    logger.info("=" * 50)
    
    logger.info("\n功能选择:")
    logger.info("1. 监听鼠标点击并保存坐标")
    logger.info("2. 查看已保存的坐标")
    logger.info("3. 清空已保存的坐标")
    
    choice = input("\n请选择功能 (1/2/3): ").strip()
    
    if choice == "1":
        listen_and_save_clicks()
    elif choice == "2":
        show_saved_coordinates()
    elif choice == "3":
        clear_coordinates()
    else:
        logger.error("无效的选择")
