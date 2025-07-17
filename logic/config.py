import json
from pathlib import Path

CONFIG_PATH = Path("config.json")

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def get_refill_day():
    config = load_config()
    value = config.get("refill_day")
    if not value:
        from datetime import date
        today = date.today()
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            config["refill_day"] = today.strftime("%Y-%m-%d")
            json.dump(config, f, indent=4, ensure_ascii=False)
        return today
    from datetime import datetime
    return datetime.strptime(value, "%Y-%m-%d").date()

def get_application_version():
    config = load_config()
    return config.get("APPLICATION_VERSION", "Unknown")
