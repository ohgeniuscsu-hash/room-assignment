from pathlib import Path
import yaml


def load_config(path: str = "config.yaml") -> dict:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {path}")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def col(config: dict, section: str, key: str) -> str:
    return config[section][key]
