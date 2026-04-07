import sys
import yaml
import logging
from typing import Optional
from pydantic import BaseModel
from martin.equipments.load_config import load_config

logger = logging.getLogger(__name__)


class GeneralConfig(BaseModel):
    SCREENSHOTS_DIR: str
    BASE_IMAGE: str
    CHECK_INTERVAL: int
    DEFAULT_CHAT_DATA_FILE: str
    KEYWORD: str
    USER_PROMPT_TEMPLATE: str
    LLM: Optional[str] = None
    STICKERS_DIR: str


class VisionConfig(BaseModel):
    DIFFERENCE_THRESHOLD: int
    CHECK_INTERVAL: int
    SAVE_IMAGES: bool
    DEFAULT_API_KEY: str
    DEFAULT_SYSTEM_PROMPT_FILE: str
    DEFAULT_USER_PROMPT_FILE: str
    DEFAULT_MODEL: str


class CoreConfig(BaseModel):
    sliding_window_size: int
    repetition_check_area: int


class MindConfig(BaseModel):
    MARTIN_IDENTITIES_TABLE: str
    YEAR: int
    DEFAULT_API_KEY: str
    DEFAULT_SYSTEM_PROMPT_TEMPLATE: str
    DEFAULT_MODEL: str


class ClawConfig(BaseModel):
    click_count: int
    click_interval: float


class EquipmentsConfig(BaseModel):
    LOG_LEVEL: str
    LOG_FILE: str
    COORDINATES_FILE: str


class SkillsConfig(BaseModel):
    FIRECRAWL_API_KEY: str
    DB_URL: str


class MartinConfig(BaseModel):
    general: GeneralConfig
    vision: VisionConfig
    core: CoreConfig
    mind: MindConfig
    claw: ClawConfig
    equipments: EquipmentsConfig
    skills: SkillsConfig


class Config(BaseModel):
    martin: MartinConfig


try:
    config = Config(**load_config("conf/config.yaml"))
except yaml.YAMLError as e:
    logger.error(f"YAML 格式错误: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"发生错误: {e}")
    sys.exit(1)
