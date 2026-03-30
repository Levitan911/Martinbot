import pandas as pd
import random
from datetime import datetime
from conf.settings import config

MARTIN_IDENTITIES_TABLE = config.martin.mind.MARTIN_IDENTITIES_TABLE
YEAR = config.martin.mind.YEAR


def get_today_martin():
    df = pd.read_csv(MARTIN_IDENTITIES_TABLE)
    
    # 用日期作为种子：年份+第几天（1-365）
    today = datetime.now()
    day_of_year = today.timetuple().tm_yday  # 1-365
    
    # 设置种子，打乱顺序
    rng = random.Random(YEAR)  # 年份作为基础种子
    indices = list(range(len(df)))
    rng.shuffle(indices)  # 每年一个固定随机顺序
    
    # 取今天的身份
    today_idx = indices[(day_of_year - 1) % len(df)]
    today_identity = df.iloc[today_idx]
    
    return today_identity


if __name__ == "__main__":
    # 使用
    martin = get_today_martin()
    print(f"今天是第{datetime.now().timetuple().tm_yday}天")
    print(f"今日马丁: {martin['身份名称']}")
