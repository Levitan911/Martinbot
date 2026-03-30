import os
import yaml


def load_config(config_path="config.yaml"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


if __name__ == "__main__":
    try:
        cfg = load_config()
        
        # 访问数据 (像操作字典一样)
        db_host = cfg['database']['host']
        log_level = cfg.get('logging', {}).get('level', 'WARNING')  # 安全获取，防止 KeyError
        
        print(f"数据库地址: {db_host}")
        print(f"日志级别: {log_level}")
        print(f"功能列表: {cfg['features']}")
        
    except yaml.YAMLError as e:
        print(f"YAML 格式错误: {e}")
    except Exception as e:
        print(f"发生错误: {e}")
