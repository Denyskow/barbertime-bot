import re
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import database as db
import keyboards as kb
from config import ADMIN_IDS
from slots import fmt_date, free_slots, next_days, today

router = Router()

PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{8,16}$")


class Booking(StatesGroup):
    service = State()
    master = State()
    date = State()
    time = State()
    phone = State()
    confirm = State()


def booking_text(b):
    return (
        f"#{b['id']} · {fmt_date(b['date'])} {b['time']}\n"
        f"{escape(b['service'])} ({b['price']} грн), майстер {escape(b['master'])}\n"
        f"{escape(b['user_name'] or '-')}, {escape(b['phone'] or '-')}"
    )


async def notify_admins(bot, text):
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Привіт, {escape(message.from_user.first_name)}! ✂️\n"
        "Тут можна записатися на стрижку — обираєте майстра і вільний час, "
        "а за пару годин до візиту я нагадаю.",
        reply_markup=kb.main_menu(),
    )


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Ок, скасував.", reply_markup=kb.main_menu())


@router.message(F.text == kb.BTN_BOOK)
async def book(message: Message, state: FSMContext):
    await state.clear()
    services = await db.get_services()
    if not services:
        await message.answer("Запис тимчасово недоступний.")
        return
    await state.set_state(Booking.service)
    await message.answer("Що робимо?", reply_markup=kb.services_kb(services))


@router.callback_query(Booking.service, F.data.startswith("svc:"))
async def pick_service(cb: CallbackQuery, state: FSMContext):
    await state.update_data(service_id=int(cb.data.split(":")[1]))
    await show_masters(cb, state)


async def show_masters(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Booking.master)
    masters = await db.get_masters()
    await cb.message.edit_text("До кого записати?", reply_markup=kb.masters_kb(masters))
    await cb.answer()


@router.callback_query(Booking.master, F.data.startswith("mst:"))
async def pick_master(cb: CallbackQuery, state: FSMContext):
    await state.update_data(master_id=int(cb.data.split(":")[1]))
    await show_dates(cb, state)


async def show_dates(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Booking.date)
    await cb.message.edit_text("Оберіть день:", reply_markup=kb.dates_kb(next_days()))
    await cb.answer()


@router.callback_query(Booking.date, F.data.startswith("date:"))
async def pick_date(cb: CallbackQuery, state: FSMContext):
    date = cb.data.split(":", 1)[1]
    data = await state.get_data()
    if "master_id" not in data:
        await cb.answer("Почніть запис спочатку", show_alert=True)
        return

    times = free_slots(date, await db.busy_times(data["master_id"], date))
    if not times:
        await cb.answer("На цей день усе зайнято", show_alert=True)
        return

    await state.update_data(date=date)
    await state.set_state(Booking.time)
    await cb.message.edit_text(f"{fmt_date(date)}, вільний час:", reply_markup=kb.times_kb(times))
    await cb.answer()


@router.callback_query(Booking.time, F.data.startswith("time:"))
async def pick_time(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    time = cb.data.split(":", 1)[1]
    await state.update_data(time=time)
    await state.set_state(Booking.phone)
    await cb.message.edit_text(f"{fmt_date(data['date'])}, {time}")
    await cb.message.answer(
        "Залиште номер телефону — кнопкою нижче або просто напишіть його.",
        reply_markup=kb.phone_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "back:svc")
async def back_services(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Booking.service)
    services = await db.get_services()
    await cb.message.edit_text("Що робимо?", reply_markup=kb.services_kb(services))
    await cb.answer()


@router.callback_query(F.data == "back:mst")
async def back_masters(cb: CallbackQuery, state: FSMContext):
    await show_masters(cb, state)


@router.callback_query(F.data == "back:date")
async def back_dates(cb: CallbackQuery, state: FSMContext):
    await show_dates(cb, state)


@router.message(Booking.phone, F.contact)
async def phone_contact(message: Message, state: FSMContext):
    await ask_confirm(message, state, message.contact.phone_number)


@router.message(Booking.phone, F.text)
async def phone_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not PHONE_RE.match(phone):
        await message.answer("Не схоже на номер, спробуйте ще раз (напр. 0671234567)")
        return
    await ask_confirm(message, state, phone)


async def ask_confirm(message: Message, state: FSMContext, phone):
    await state.update_data(phone=phone)
    data = await state.get_data()
    service = await db.get_service(data["service_id"])
    master = await db.get_master(data["master_id"])
    await state.set_state(Booking.confirm)

    await message.answer("Дякую!", reply_markup=kb.main_menu())
    await message.answer(
        f"{escape(service['name'])} — {service['price']} грн\n"
        f"Майстер: {escape(master['name'])}\n"
        f"Коли: {fmt_date(data['date'])}, {data['time']}\n"
        f"Телефон: {escape(phone)}\n\n"
        "Все вірно?",
        reply_markup=kb.confirm_kb(),
    )


@router.callback_query(Booking.confirm, F.data == "confirm:yes")
async def confirm(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    booking_id = await db.create_booking(
        cb.from_user.id, cb.from_user.full_name, data["phone"],
        data["service_id"], data["master_id"], data["date"], data["time"],
    )
    if booking_id is None:
        await cb.message.edit_text("😔 На жаль, цей час щойно зайняли. Спробуйте обрати інший.")
        await cb.answer()
        return

    await cb.message.edit_text(
        f"✅ Готово, чекаємо вас {fmt_date(data['date'])} о {data['time']}.\n"
        "Скасувати можна в «📋 Мої записи»."
    )
    await cb.answer()

    booking = await db.get_booking(booking_id)
    await notify_admins(cb.bot, "🆕 <b>Новий запис</b>\n" + booking_text(booking))


@router.callback_query(Booking.confirm, F.data == "confirm:no")
async def confirm_no(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Запис скасовано.")
    await cb.answer()


@router.message(F.text == kb.BTN_MY)
async def my_bookings(message: Message, state: FSMContext):
    await state.clear()
    bookings = await db.user_bookings(message.from_user.id, today())
    if not bookings:
        await message.answer("Активних записів немає.")
        return

    lines = [
        f"{fmt_date(b['date'])} о {b['time']} — {escape(b['service'])}, {escape(b['master'])}"
        for b in bookings
    ]
    await message.answer("\n".join(lines), reply_markup=kb.my_bookings_kb(bookings))


@router.callback_query(F.data.startswith("ucancel:"))
async def user_cancel(cb: CallbackQuery):
    booking_id = int(cb.data.split(":")[1])
    booking = await db.get_booking(booking_id)
    if not await db.cancel_booking(booking_id, user_id=cb.from_user.id):
        await cb.answer("Цей запис уже скасовано", show_alert=True)
        return
    await cb.message.edit_text(f"Запис на {fmt_date(booking['date'])} {booking['time']} скасовано.")
    await cb.answer()
    await notify_admins(cb.bot, "❌ <b>Скасування</b>\n" + booking_text(booking))


# старі кнопки після перезапуску бота / скидання стану
@router.callback_query(StateFilter("*"))
async def old_button(cb: CallbackQuery):
    await cb.answer("Кнопка вже неактивна, почніть запис заново", show_alert=True)
