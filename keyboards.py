from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from slots import fmt_date

BTN_BOOK = "📅 Записатися"
BTN_MY = "📋 Мої записи"


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_BOOK), KeyboardButton(text=BTN_MY)]],
        resize_keyboard=True,
    )


def phone_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Надіслати номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def services_kb(services):
    kb = InlineKeyboardBuilder()
    for s in services:
        kb.button(text=f"{s['name']} · {s['price']} грн", callback_data=f"svc:{s['id']}")
    kb.adjust(1)
    return kb.as_markup()


def masters_kb(masters):
    kb = InlineKeyboardBuilder()
    for m in masters:
        kb.button(text=m["name"], callback_data=f"mst:{m['id']}")
    kb.button(text="« Назад", callback_data="back:svc")
    kb.adjust(1)
    return kb.as_markup()


def dates_kb(dates):
    kb = InlineKeyboardBuilder()
    for d in dates:
        kb.button(text=fmt_date(d), callback_data=f"date:{d}")
    kb.button(text="« Назад", callback_data="back:mst")
    kb.adjust(3)
    return kb.as_markup()


def times_kb(times):
    kb = InlineKeyboardBuilder()
    for t in times:
        kb.button(text=t, callback_data=f"time:{t}")
    kb.button(text="« Назад", callback_data="back:date")
    kb.adjust(4)
    return kb.as_markup()


def confirm_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Підтвердити", callback_data="confirm:yes")
    kb.button(text="❌ Скасувати", callback_data="confirm:no")
    return kb.as_markup()


def my_bookings_kb(bookings):
    kb = InlineKeyboardBuilder()
    for b in bookings:
        kb.button(text=f"Скасувати {fmt_date(b['date'])} {b['time']}", callback_data=f"ucancel:{b['id']}")
    kb.adjust(1)
    return kb.as_markup()


def admin_bookings_kb(bookings):
    kb = InlineKeyboardBuilder()
    for b in bookings:
        kb.button(text=f"✕ #{b['id']}", callback_data=f"acancel:{b['id']}")
    kb.adjust(4)
    return kb.as_markup()
