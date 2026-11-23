import sqlite3
from contextlib import asynccontextmanager

import aiosqlite

from config import DB_PATH

BOOKING_SQL = """
SELECT b.id, b.user_id, b.user_name, b.phone, b.date, b.time, b.status,
       s.name AS service, s.price, m.name AS master
FROM bookings b
JOIN services s ON s.id = b.service_id
JOIN masters m ON m.id = b.master_id
"""


@asynccontextmanager
async def connect():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db


async def init_db():
    async with connect() as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS masters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT,
                phone TEXT,
                service_id INTEGER NOT NULL,
                master_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                reminded INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            -- щоб двоє не записались на один час до одного майстра
            CREATE UNIQUE INDEX IF NOT EXISTS ux_slot
                ON bookings(master_id, date, time) WHERE status = 'active';
        """)

        cur = await db.execute("SELECT COUNT(*) FROM services")
        if (await cur.fetchone())[0] == 0:
            await db.executemany("INSERT INTO services(name, price) VALUES (?, ?)", [
                ("Чоловіча стрижка", 400),
                ("Стрижка бороди", 250),
                ("Стрижка + борода", 600),
            ])
            await db.executemany("INSERT INTO masters(name) VALUES (?)", [("Олександр",), ("Максим",)])
        await db.commit()


async def fetch_all(sql, params=()):
    async with connect() as db:
        cur = await db.execute(sql, params)
        return await cur.fetchall()


async def fetch_one(sql, params=()):
    async with connect() as db:
        cur = await db.execute(sql, params)
        return await cur.fetchone()


async def execute(sql, params=()):
    async with connect() as db:
        cur = await db.execute(sql, params)
        await db.commit()
        return cur


# services / masters

async def get_services():
    return await fetch_all("SELECT * FROM services WHERE active = 1 ORDER BY id")


async def get_service(service_id):
    return await fetch_one("SELECT * FROM services WHERE id = ?", (service_id,))


async def add_service(name, price):
    cur = await execute("INSERT INTO services(name, price) VALUES (?, ?)", (name, price))
    return cur.lastrowid


async def hide_service(service_id):
    cur = await execute("UPDATE services SET active = 0 WHERE id = ? AND active = 1", (service_id,))
    return cur.rowcount > 0


async def get_masters():
    return await fetch_all("SELECT * FROM masters WHERE active = 1 ORDER BY id")


async def get_master(master_id):
    return await fetch_one("SELECT * FROM masters WHERE id = ?", (master_id,))


async def add_master(name):
    cur = await execute("INSERT INTO masters(name) VALUES (?)", (name,))
    return cur.lastrowid


async def hide_master(master_id):
    cur = await execute("UPDATE masters SET active = 0 WHERE id = ? AND active = 1", (master_id,))
    return cur.rowcount > 0


# bookings

async def busy_times(master_id, date):
    rows = await fetch_all(
        "SELECT time FROM bookings WHERE master_id = ? AND date = ? AND status = 'active'",
        (master_id, date),
    )
    return {r["time"] for r in rows}


async def create_booking(user_id, user_name, phone, service_id, master_id, date, time):
    try:
        cur = await execute(
            "INSERT INTO bookings(user_id, user_name, phone, service_id, master_id, date, time) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, user_name, phone, service_id, master_id, date, time),
        )
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None  # слот вже зайняли


async def get_booking(booking_id):
    return await fetch_one(BOOKING_SQL + " WHERE b.id = ?", (booking_id,))


async def user_bookings(user_id, from_date):
    return await fetch_all(
        BOOKING_SQL + " WHERE b.user_id = ? AND b.status = 'active' AND b.date >= ? ORDER BY b.date, b.time",
        (user_id, from_date),
    )


async def bookings_between(date_from, date_to):
    return await fetch_all(
        BOOKING_SQL + " WHERE b.status = 'active' AND b.date BETWEEN ? AND ? ORDER BY b.date, b.time",
        (date_from, date_to),
    )


async def cancel_booking(booking_id, user_id=None):
    sql = "UPDATE bookings SET status = 'cancelled' WHERE id = ? AND status = 'active'"
    params = [booking_id]
    if user_id is not None:
        sql += " AND user_id = ?"
        params.append(user_id)
    cur = await execute(sql, params)
    return cur.rowcount > 0


async def not_reminded(dates):
    q = ",".join("?" * len(dates))
    return await fetch_all(
        BOOKING_SQL + f" WHERE b.status = 'active' AND b.reminded = 0 AND b.date IN ({q})", dates
    )


async def set_reminded(booking_id):
    await execute("UPDATE bookings SET reminded = 1 WHERE id = ?", (booking_id,))
