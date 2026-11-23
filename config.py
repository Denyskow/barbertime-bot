import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
DB_PATH = os.getenv("DB_PATH", "bot.db")
TZ = ZoneInfo(os.getenv("TIMEZONE", "Europe/Kyiv"))

WORK_START = 10
WORK_END = 19
SLOT_MINUTES = 60
DAYS_AHEAD = 7
REMIND_BEFORE = 120  # хв
