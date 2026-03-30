import os
import time
import numpy as np
import pyautogui
import logging
from PIL import ImageGrab
from datetime import datetime
from conf.settings import config
from martin.equipments.wechat_locator import show_saved_coordinates

logger = logging.getLogger(__name__)

DIFFERENCE_THRESHOLD = config.martin.vision.DIFFERENCE_THRESHOLD
CHECK_INTERVAL = config.martin.vision.CHECK_INTERVAL
SAVE_IMAGES = config.martin.vision.SAVE_IMAGES
IMAGE_DIR = config.martin.general.SCREENSHOTS_DIR


def calculate_monitor_area(coordinates):
    """
    根据坐标计算监控区域
    
    Args:
        coordinates: 坐标列表 [(x1, y1), (x2, y2), ...]
    
    Returns:
        监控区域 (left, top, right, bottom) 或 None
    """
    if not coordinates or len(coordinates) < 2:
        logger.error("需要至少2个坐标点来确定监控区域")
        return None
    
    coordinates = coordinates[:-1]
    x_coords = [coord[0] for coord in coordinates]
    y_coords = [coord[1] for coord in coordinates]
    
    left = min(x_coords)
    top = min(y_coords)
    right = max(x_coords)
    bottom = max(y_coords)
    
    return (left, top, right, bottom)


def get_screen_info():
    """
    获取屏幕信息
    
    Returns:
        屏幕尺寸 (width, height)
    """
    try:
        width, height = pyautogui.size()
        logger.info(f"检测到屏幕尺寸: 宽={width}, 高={height}")
        return width, height
    except Exception as e:
        logger.error(f"获取屏幕信息失败: {e}")
        return 1920, 1080


def validate_monitor_area(monitor_area, screen_size):
    """
    验证监控区域是否在屏幕范围内
    
    Args:
        monitor_area: 监控区域 (left, top, right, bottom)
        screen_size: 屏幕尺寸 (width, height)
    
    Returns:
        是否有效
    """
    left, top, right, bottom = monitor_area
    screen_width, screen_height = screen_size
    
    logger.info(f"\n监控区域验证:")
    logger.info(f" 左上角: ({left}, {top})")
    logger.info(f" 右下角: ({right}, {bottom})")
    logger.info(f" 宽度: {right - left}, 高度: {bottom - top}")
    logger.info(f" 屏幕范围: (0, 0) 到 ({screen_width}, {screen_height})")
    
    if left < 0 or top < 0 or right > screen_width or bottom > screen_height:
        logger.warning(f"  警告: 监控区域超出屏幕范围！")
        logger.warning(f"  建议: 请重新保存坐标点，确保在主显示器范围内")
        return False
    
    return True


def save_image(image, filename):
    """
    保存图像到文件
    
    Args:
        image: PIL Image 对象
        filename: 文件名
    """
    if not SAVE_IMAGES:
        return
    
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
    
    filepath = os.path.join(IMAGE_DIR, filename)
    image.save(filepath)
    logger.info(f"图像已保存: {filepath}")


def screen_monitor():
    """
    屏幕监控主函数
    """
    logger.info("\n屏幕监视器")
    logger.info("=" * 50)
    
    screen_size = get_screen_info()
    
    coordinates = show_saved_coordinates()
    
    if not coordinates:
        logger.error("\n无法获取坐标，请先运行 wechat_locator.py 保存坐标")
        return
    
    monitor_area = calculate_monitor_area(coordinates)
    if not monitor_area:
        return
    
    if not validate_monitor_area(monitor_area, screen_size):
        logger.error("\n监控区域无效，请重新保存坐标")
        return
    
    logger.info(f"\n差异阈值: {DIFFERENCE_THRESHOLD}")
    logger.info(f"检测间隔: {CHECK_INTERVAL} 秒")
    logger.info(f"保存图像: {'是' if SAVE_IMAGES else '否'}")
    logger.info("=" * 50)
    
    try:
        logger.info("正在截取基准图像...")
        base_image = ImageGrab.grab(monitor_area)
        last_screen = np.array(base_image, dtype=np.uint8)
        logger.info(f"基准图像尺寸: {last_screen.shape}, 数据类型: {last_screen.dtype}")
        logger.info(f"基准图像像素范围: {last_screen.min()} - {last_screen.max()}")
        
        if SAVE_IMAGES:
            save_image(base_image, f"base_image.png")
        
        logger.info("基准图像已截取，开始监控...")
        logger.info("按 Ctrl+C 停止监控")
        
        change_count = 0
        frame_count = 0
        
        while True:
            current_image = ImageGrab.grab(monitor_area)
            current_screen = np.array(current_image, dtype=np.uint8)
            
            difference = np.sum(np.abs(current_screen.astype(np.int32) - last_screen.astype(np.int32)))
            
            if difference > DIFFERENCE_THRESHOLD:
                change_count += 1
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"\n[{timestamp}] 检测到变化！差异值: {difference} (累计变化: {change_count})")
                last_screen = current_screen

                if SAVE_IMAGES:
                    frame_count += 1
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"ts_{timestamp}_frame_{frame_count}.png"
                    save_image(current_image, filename)
            
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info(f"\n\n监控已停止")
        logger.info(f"累计检测到 {change_count} 次变化")
        if SAVE_IMAGES:
            logger.info(f"图像保存在目录: {os.path.abspath(IMAGE_DIR)}")
    except Exception as e:
        logger.error(f"\n监控过程中发生异常 - {e}")


if __name__ == "__main__":
    screen_monitor()
