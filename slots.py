from datetime import datetime, timedelta

from config import DAYS_AHEAD, SLOT_MINUTES, TZ, WORK_END, WORK_START

WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]


def now():
    return datetime.now(TZ)


def today():
    return now().strftime("%Y-%m-%d")


def next_days():
    start = now().date()
    return [(start + timedelta(days=i)).isoformat() for i in range(DAYS_AHEAD)]


def day_slots():
    result = []
    minutes = WORK_START * 60
    while minutes + SLOT_MINUTES <= WORK_END * 60:
        result.append(f"{minutes // 60:02d}:{minutes % 60:02d}")
        minutes += SLOT_MINUTES
    return result


def free_slots(date, busy):
    current = now()
    free = []
    for t in day_slots():
        if t in busy:
            continue
        if datetime.fromisoformat(f"{date} {t}").replace(tzinfo=TZ) <= current:
            continue
        free.append(t)
    return free


def fmt_date(date):
    d = datetime.fromisoformat(date)
    return f"{WEEKDAYS[d.weekday()]}, {d:%d.%m}"
