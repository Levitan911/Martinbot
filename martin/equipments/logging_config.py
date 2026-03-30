import os
import sys
import logging
from conf.settings import config
from logging.handlers import RotatingFileHandler

LOG_LEVEL = config.martin.equipments.LOG_LEVEL
LOG_FILE = config.martin.equipments.LOG_FILE
LOG_FORMAT = "%(asctime)s|%(levelname)-8s|%(filename)s|%(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class BaseFormatter(logging.Formatter):
    """基类：处理换行符前置"""
    def _handle_leading_newlines(self, record):
        """提取并处理开头的换行符，返回 (newline_str, clean_msg)"""
        original_msg = record.getMessage()
        stripped = original_msg.lstrip('\n')
        newline_cnt = len(original_msg) - len(stripped)
        
        if newline_cnt > 0:
            # 创建临时 record 用于格式化，避免修改原 record
            return '\n' * newline_cnt, stripped
        
        return '', original_msg


class ColoredFormatter(BaseFormatter):
    """彩色控制台日志"""
    COLORS = {
        'DEBUG': '\033[94m',
        'INFO': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[95m',
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        # 处理换行
        newline_prefix, clean_msg = self._handle_leading_newlines(record)
        
        # 创建临时 record 避免副作用
        temp_record = logging.makeLogRecord(record.__dict__)
        temp_record.msg = clean_msg
        temp_record.args = ()
        
        # 加颜色
        levelname = temp_record.levelname
        color = self.COLORS.get(levelname, self.COLORS['RESET'])
        temp_record.levelname = f"{color}{levelname}{self.COLORS['RESET']}"
        
        # 格式化
        result = super().format(temp_record)
        return newline_prefix + result


class PlainFormatter(BaseFormatter):
    """纯文本文件日志（无颜色）"""
    def format(self, record):
        newline_prefix, clean_msg = self._handle_leading_newlines(record)
        
        # 创建临时 record
        temp_record = logging.makeLogRecord(record.__dict__)
        temp_record.msg = clean_msg
        temp_record.args = ()
        
        result = super().format(temp_record)
        return newline_prefix + result


def setup_logging(log_file=LOG_FILE, max_bytes=10*1024*1024, backup_count=5):
    level = getattr(logging, LOG_LEVEL, logging.INFO)
    
    # 创建目录
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # 控制台：彩色
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(ColoredFormatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    
    # 文件：纯文本
    file_handler = RotatingFileHandler(
        log_file, mode='a', encoding='utf-8',
        maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(PlainFormatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    
    # 配置
    logging.basicConfig(
        level=level,
        handlers=[console, file_handler],
        force=True
    )
    
    # 抑制第三方库
    for name in ["requests", "urllib3", "httpx", "zai"]:
        logging.getLogger(name).setLevel(logging.WARNING)


if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 测试
    logger.info("普通消息")
    logger.info("\n带前置换行的消息")
    logger.info("参数测试: %s", "hello")
