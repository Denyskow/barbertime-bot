from datetime import timedelta
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

import database as db
from config import ADMIN_IDS
from handlers.client import booking_text
from keyboards import admin_bookings_kb
from slots import fmt_date, now

router = Router()
router.message.filter(F.from_user.id.in_(ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(ADMIN_IDS))

HELP = """<b>Команди</b>
/today, /tomorrow, /week — записи
/services — послуги
/add_service Назва;ціна
/del_service id
/masters — майстри
/add_master Ім'я
/del_master id"""


@router.message(Command("admin"))
async def admin_help(message: Message):
    await message.answer(HELP)


async def send_bookings(message, date_from, date_to, title):
    bookings = await db.bookings_between(date_from, date_to)
    if not bookings:
        await message.answer(f"{title}: пусто")
        return
    text = f"<b>{title}</b> — {len(bookings)}\n\n" + "\n\n".join(booking_text(b) for b in bookings)
    await message.answer(text, reply_markup=admin_bookings_kb(bookings))


@router.message(Command("today"))
async def today_cmd(message: Message):
    d = now().date().isoformat()
    await send_bookings(message, d, d, f"Сьогодні ({fmt_date(d)})")


@router.message(Command("tomorrow"))
async def tomorrow_cmd(message: Message):
    d = (now() + timedelta(days=1)).date().isoformat()
    await send_bookings(message, d, d, f"Завтра ({fmt_date(d)})")


@router.message(Command("week"))
async def week_cmd(message: Message):
    start = now().date()
    await send_bookings(message, start.isoformat(), (start + timedelta(days=6)).isoformat(), "Тиждень")


@router.callback_query(F.data.startswith("acancel:"))
async def admin_cancel(cb: CallbackQuery):
    booking_id = int(cb.data.split(":")[1])
    booking = await db.get_booking(booking_id)
    if not await db.cancel_booking(booking_id):
        await cb.answer("Вже скасовано", show_alert=True)
        return

    await cb.answer(f"#{booking_id} скасовано")
    try:
        await cb.bot.send_message(
            booking["user_id"],
            f"Ваш запис на {fmt_date(booking['date'])} о {booking['time']} скасовано. "
            "Вибачте за незручності — оберіть, будь ласка, інший час.",
        )
    except Exception:
        pass


@router.message(Command("services"))
async def services_cmd(message: Message):
    rows = await db.get_services()
    text = "\n".join(f"{s['id']}. {escape(s['name'])} — {s['price']} грн" for s in rows)
    await message.answer(text or "Послуг немає")


@router.message(Command("add_service"))
async def add_service_cmd(message: Message, command: CommandObject):
    try:
        name, price = command.args.split(";")
        name, price = name.strip(), int(price)
        assert name and price > 0
    except (AttributeError, ValueError, AssertionError):
        await message.answer("Формат: /add_service Укладка;300")
        return
    new_id = await db.add_service(name, price)
    await message.answer(f"Додано: {new_id}. {escape(name)} — {price} грн")


@router.message(Command("del_service"))
async def del_service_cmd(message: Message, command: CommandObject):
    if not (command.args or "").strip().isdigit():
        await message.answer("Формат: /del_service 3")
        return
    ok = await db.hide_service(int(command.args))
    await message.answer("Прибрав" if ok else "Нема такої послуги")


@router.message(Command("masters"))
async def masters_cmd(message: Message):
    rows = await db.get_masters()
    text = "\n".join(f"{m['id']}. {escape(m['name'])}" for m in rows)
    await message.answer(text or "Майстрів немає")


@router.message(Command("add_master"))
async def add_master_cmd(message: Message, command: CommandObject):
    name = (command.args or "").strip()
    if not name:
        await message.answer("Формат: /add_master Ім'я")
        return
    new_id = await db.add_master(name)
    await message.answer(f"Додано: {new_id}. {escape(name)}")


@router.message(Command("del_master"))
async def del_master_cmd(message: Message, command: CommandObject):
    if not (command.args or "").strip().isdigit():
        await message.answer("Формат: /del_master 2")
        return
    ok = await db.hide_master(int(command.args))
    await message.answer("Прибрав" if ok else "Нема такого майстра")
