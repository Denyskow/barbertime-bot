import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db
from config import REMIND_BEFORE, TZ
from slots import now

log = logging.getLogger(__name__)


async def remind(bot):
    current = now()
    days = [current.date().isoformat(), (current + timedelta(days=1)).date().isoformat()]

    for b in await db.not_reminded(days):
        visit = datetime.fromisoformat(f"{b['date']} {b['time']}").replace(tzinfo=TZ)
        if not current < visit <= current + timedelta(minutes=REMIND_BEFORE):
            continue
        try:
            await bot.send_message(
                b["user_id"],
                f"⏰ Нагадуємо: сьогодні о {b['time']} — {b['service']}, майстер {b['master']}.",
            )
        except Exception as e:
            log.warning("reminder %s failed: %s", b["id"], e)
        await db.set_reminded(b["id"])


def create_scheduler(bot):
    scheduler = AsyncIOScheduler(timezone=TZ)
    scheduler.add_job(remind, "interval", minutes=1, args=[bot])
    return scheduler
