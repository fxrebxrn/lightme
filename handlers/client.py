from aiogram import Dispatcher, types
from aiogram.utils.callback_data import CallbackData
from database.db import get_db, get_user_settings, set_user_setting
import config
from locales.strings import get_text
from services.scheduler import parse_localized_datetime
from datetime import datetime, timedelta
import pytz
import sqlite3
import uuid

COMPARE_STATE = {}
# Часовой пояс Киева
UA_TZ = pytz.timezone('Europe/Kyiv')

def format_display_date(date_str: str):
    """Перетворює дату з YYYY-MM-DD у DD.MM.YYYY для показу користувачу."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
    except Exception:
        return date_str

def format_display_datetime(dt_str: str):
    """Перетворює datetime з YYYY-MM-DD HH:MM:SS у DD.MM.YYYY HH:MM:SS."""
    try:
        return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M:%S')
    except Exception:
        return dt_str

# CallbackData
cb_lang = CallbackData("lang", "code")
cb_menu = CallbackData("menu", "action", "val")
# Обновлено: добавлен параметр date
cb_sched = CallbackData("sched", "comp", "queue", "date") 
cb_notify = CallbackData("notify", "key", "val")

# --- Утилиты работы с сохранёнными сравнениями в БД ---
def ensure_compares_table():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT,
                comp1 TEXT NOT NULL,
                queue1 TEXT NOT NULL,
                comp2 TEXT NOT NULL,
                queue2 TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def save_compare_to_db(user_id, name, comp1, q1, comp2, q2):
    ensure_compares_table()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO compares (user_id, name, comp1, queue1, comp2, queue2) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, comp1, q1, comp2, q2)
        )
        conn.commit()
        return cur.lastrowid
        
def count_user_compares(user_id):
    ensure_compares_table()
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM compares WHERE user_id=?", (user_id,)).fetchone()
    return row['c'] if row else 0

def list_user_compares(user_id):
    ensure_compares_table()
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, comp1, queue1, comp2, queue2, created_at FROM compares WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    return rows


def get_compare_by_id(cid):
    ensure_compares_table()
    with get_db() as conn:
        row = conn.execute("SELECT id, user_id, name, comp1, queue1, comp2, queue2, created_at FROM compares WHERE id=?", (cid,)).fetchone()
    return row


def delete_compare_by_id(cid):
    ensure_compares_table()
    with get_db() as conn:
        conn.execute("DELETE FROM compares WHERE id=?", (cid,))
        conn.commit()


# --- Утилиты времени / интервалы ---
def normalize_time_and_offset(time_str: str):
    t = time_str.strip()
    if t == '24:00':
        return '00:00', 1
    return t, 0


def minutes_from_str(time_str: str):
    norm, day_off = normalize_time_and_offset(time_str)
    hh, mm = map(int, norm.split(':'))
    return hh * 60 + mm + day_off * 1440


def format_minutes(m):
    if m >= 1440:
        if m == 1440:
            return "24:00"
        m = m % 1440
    hh = m // 60
    mm = m % 60
    return f"{hh:02d}:{mm:02d}"

def _format_hours_decimal(minutes: int):
    hours = minutes / 60
    if hours.is_integer():
        return str(int(hours))
    return f"{hours:.1f}".rstrip('0').rstrip('.')

def merge_intervals(intervals):
    if not intervals:
        return []
    intervals = sorted(intervals, key=lambda x: x[0])
    merged = []
    cur_s, cur_e = intervals[0]
    for s, e in intervals[1:]:
        if s <= cur_e:
            cur_e = max(cur_e, e)
        else:
            merged.append((cur_s, cur_e))
            cur_s, cur_e = s, e
    merged.append((cur_s, cur_e))
    return merged


def invert_intervals(offs, day_minutes=1440):
    ons = []
    prev = 0
    for s, e in offs:
        if prev < s:
            ons.append((prev, s))
        prev = max(prev, e)
    if prev < day_minutes:
        ons.append((prev, day_minutes))
    return ons


def intersect_intervals(a, b):
    res = []
    i, j = 0, 0
    while i < len(a) and j < len(b):
        s = max(a[i][0], b[j][0])
        e = min(a[i][1], b[j][1])
        if s < e:
            res.append((s, e))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return res


# --- Клавиатуры ---
def lang_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🇺🇦 Українська", callback_data=cb_lang.new(code="uk"), style="primary"),
           types.InlineKeyboardButton("🇷🇺 Русский", callback_data=cb_lang.new(code="ru"), style="primary"))
    return kb


def main_menu_kb(lang):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(get_text(lang, 'btn_add_queue'), get_text(lang, 'btn_my_queues'))
    kb.row(get_text(lang, 'btn_schedules'), get_text(lang, 'btn_compare'))
    kb.row(get_text(lang, 'btn_settings'), get_text(lang, 'btn_support'))
    return kb


def queues_kb_for_compare(company, lang, phase):
    # phase: 'c1' or 'c2' to decide back-button behavior
    queues = ["1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "4.1", "4.2", "5.1", "5.2", "6.1", "6.2"]
    kb = types.InlineKeyboardMarkup()
    # add in rows of 3
    row = []
    for i, q in enumerate(queues, 1):
        row.append(types.InlineKeyboardButton(q, callback_data=f"cmp_q{('1' if phase=='c1' else '2')}|{company}|{q}", style="primary"))
        if i % 3 == 0:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    # Back button goes to company selection for this phase
    back_cb = "cmp_back_to_c1" if phase == 'c1' else "cmp_back_to_c2"
    kb.add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data=back_cb, style="danger"))
    return kb


# --- Обработчики сравнения ---
async def compare_menu(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(get_text(lang, 'btn_compare_new'), get_text(lang, 'btn_compare_my'))
    kb.row(get_text(lang, 'back'))
    await message.answer(get_text(lang, 'cmp_menu_text'), reply_markup=kb)


async def compare_new_start(message: types.Message):
    user_id = message.from_user.id
    COMPARE_STATE.pop(user_id, None)
    lang = get_user_lang(user_id)
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("ДТЕК", callback_data=f"cmp_c1|ДТЕК", style="primary"),
           types.InlineKeyboardButton("ЦЕК", callback_data=f"cmp_c1|ЦЕК", style="primary"))
    kb.add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data="cmp_back_to_compare_menu", style="danger"))
    await message.answer(get_text(lang, 'cmp_choose_first'), reply_markup=kb)


async def compare_my_list(message: types.Message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    rows = list_user_compares(user_id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    if not rows:
        # покажем текст и кнопку назад в compare menu
        kb2 = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data="cmp_back_to_compare_menu", style="danger"))
        await message.answer(get_text(lang, 'cmp_no_saved'), reply_markup=kb2)
        return
    for r in rows:
        name = r['name'] or f"{r['comp1']} {r['queue1']} + {r['comp2']} {r['queue2']}"
        kb.add(types.InlineKeyboardButton(f"{name}", callback_data=f"cmp_run_saved|{r['id']}|today", style="primary"))
    kb.add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data="cmp_back_to_compare_menu", style="danger"))
    await message.answer(get_text(lang, 'cmp_list_header'), reply_markup=kb)


# Router for inline callbacks related to compare
async def compare_callback_router(call: types.CallbackQuery):
    data = call.data or ""
    user_id = call.from_user.id
    lang = get_user_lang(user_id)

    # Back to compare menu
    if data == "cmp_back_to_compare_menu":
        # show compare menu (reply keyboard)
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row(get_text(lang, 'btn_compare_new'), get_text(lang, 'btn_compare_my'))
        kb.row(get_text(lang, 'back'))
        try:
            await call.message.edit_text(get_text(lang, 'cmp_menu_text'), reply_markup=kb)
        except Exception:
            await call.message.answer(get_text(lang, 'cmp_menu_text'), reply_markup=kb)
        await call.answer()
        return

    # Back to company selection for c1/c2
    if data == "cmp_back_to_c1":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("ДТЕК", callback_data=f"cmp_c1|ДТЕК", style="primary"),
               types.InlineKeyboardButton("ЦЕК", callback_data=f"cmp_c1|ЦЕК", style="primary"))
        kb.add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data="cmp_back_to_compare_menu", style="danger"))
        await call.message.edit_text(get_text(lang, 'cmp_choose_first'), reply_markup=kb)
        await call.answer()
        return
    if data == "cmp_back_to_c2":
        # if first is chosen, we still ask second company
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("ДТЕК", callback_data="cmp_c2|ДТЕК", style="primary"),
               types.InlineKeyboardButton("ЦЕК", callback_data="cmp_c2|ЦЕК", style="primary"))
        kb.add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data="cmp_back_to_compare_menu", style="danger"))
        await call.message.edit_text(get_text(lang, 'cmp_choose_second'), reply_markup=kb)
        await call.answer()
        return

    # cmp_c1|COMP
    if data.startswith("cmp_c1|"):
        _, comp = data.split("|", 1)
        await call.message.edit_text(get_text(lang, 'choose_queue', company=comp), reply_markup=queues_kb_for_compare(comp, lang, 'c1'))
        await call.answer()
        return

    # cmp_q1|COMP|Q
    if data.startswith("cmp_q1|"):
        try:
            _, comp, q = data.split("|", 2)
        except ValueError:
            await call.answer("Invalid data", show_alert=True)
            return
        COMPARE_STATE[user_id] = {'first': (comp, q)}
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("ДТЕК", callback_data="cmp_c2|ДТЕК", style="primary"),
               types.InlineKeyboardButton("ЦЕК", callback_data="cmp_c2|ЦЕК", style="primary"))
        kb.add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data="cmp_back_to_c1", style="danger"))
        await call.message.edit_text(get_text(lang, 'cmp_choose_second'), reply_markup=kb)
        await call.answer()
        return

    # cmp_c2|COMP
    if data.startswith("cmp_c2|"):
        _, comp = data.split("|", 1)
        await call.message.edit_text(get_text(lang, 'choose_queue', company=comp), reply_markup=queues_kb_for_compare(comp, lang, 'c2'))
        await call.answer()
        return

    # cmp_q2|COMP|Q
    if data.startswith("cmp_q2|"):
        try:
            _, comp, q = data.split("|", 2)
        except ValueError:
            await call.answer("Invalid data", show_alert=True)
            return
        state = COMPARE_STATE.get(user_id)
        if not state or 'first' not in state:
            await call.answer(get_text(lang, 'cmp_error_restart'), show_alert=True)
            return
        state['second'] = (comp, q)
        comp1, q1 = state['first']
        comp2, q2 = state['second']
        kb = types.InlineKeyboardMarkup(row_width=2)
        kb.add(types.InlineKeyboardButton(get_text(lang, 'today_label'), callback_data=f"cmp_run|{comp1}|{q1}|{comp2}|{q2}|today", style="primary"),
               types.InlineKeyboardButton(get_text(lang, 'tomorrow_label'), callback_data=f"cmp_run|{comp1}|{q1}|{comp2}|{q2}|tomorrow", style="primary"))
        kb.add(types.InlineKeyboardButton(get_text(lang, 'cmp_save_button'), callback_data=f"cmp_save|{comp1}|{q1}|{comp2}|{q2}", style="success"))
        kb.add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data="cmp_back_to_c2", style="danger"))
        await call.message.edit_text(get_text(lang, 'cmp_ready_preview', comp1=comp1, queue1=q1, comp2=comp2, queue2=q2), reply_markup=kb)
        await call.answer()
        return

    # cmp_run|comp1|q1|comp2|q2|day
    if data.startswith("cmp_run|"):
        parts = data.split("|")
        if len(parts) != 6:
            await call.answer("Invalid data", show_alert=True)
            return
        _, comp1, q1, comp2, q2, day = parts
        await run_compare_and_show(call, comp1, q1, comp2, q2, day, lang)
        await call.answer()
        return

    # cmp_save|comp1|q1|comp2|q2
    if data.startswith("cmp_save|"):
        _, comp1, q1, comp2, q2 = data.split("|")
        # Ограничение: максимум 5 сохранённых сравнений на пользователя
        limit = 5
        if count_user_compares(user_id) >= limit:
            await call.answer(get_text(lang, 'cmp_limit_reached', limit=limit), show_alert=True)
            return
    
        name = f"{comp1} {q1} + {comp2} {q2}"
        try:
            save_compare_to_db(user_id, name, comp1, q1, comp2, q2)
            await call.answer(get_text(lang, 'cmp_saved_ok'), show_alert=True)
            await call.message.edit_text(
                get_text(lang, 'cmp_saved_msg', name=name),
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton(get_text(lang, 'back'), callback_data="cmp_back_to_compare_menu", style="danger")
                )
            )
        except Exception:
            await call.answer(get_text(lang, 'cmp_saved_fail'), show_alert=True)
        return

    # cmp_run_saved|id|day
    if data.startswith("cmp_run_saved|"):
        _, cid, day = data.split("|")
        row = get_compare_by_id(int(cid))
        if not row:
            await call.answer(get_text(lang, 'cmp_no_saved'), show_alert=True)
            return
        comp1, q1, comp2, q2 = row['comp1'], row['queue1'], row['comp2'], row['queue2']
        await run_compare_and_show(call, comp1, q1, comp2, q2, day, lang, saved_id=row['id'])
        await call.answer()
        return

    # cmp_del|id
    if data.startswith("cmp_del|"):
        _, cid = data.split("|")
        delete_compare_by_id(int(cid))
        await call.answer(get_text(lang, 'cmp_deleted_ok'), show_alert=True)
        # show updated list
        await compare_my_list(call.message)
        return

    # cmp_details|comp1|q1|comp2|q2|day
    if data.startswith("cmp_details|"):
        parts = data.split("|")
        if len(parts) != 6:
            await call.answer("Invalid data", show_alert=True)
            return
        _, comp1, q1, comp2, q2, day = parts
        await show_compare_details(call, comp1, q1, comp2, q2, day, lang)
        await call.answer()
        return

    await call.answer()


# Сборка и показ результата сравнения
async def run_compare_and_show(call: types.CallbackQuery, comp1, q1, comp2, q2, day, lang, saved_id=None):
    now = datetime.now(UA_TZ)
    if day == 'tomorrow':
        target_date = (now + timedelta(days=1)).date()
    else:
        target_date = now.date()
    date_str = target_date.strftime('%Y-%m-%d')

    with get_db() as conn:
        rows1 = conn.execute("SELECT off_time, on_time FROM schedules WHERE company=? AND queue=? AND date=?", (comp1, q1, date_str)).fetchall()
        rows2 = conn.execute("SELECT off_time, on_time FROM schedules WHERE company=? AND queue=? AND date=?", (comp2, q2, date_str)).fetchall()

    # If either queue has no schedule entries -> show friendly "no data" (user expects that)
    if not rows1 or not rows2:
        kb = types.InlineKeyboardMarkup()
        # если пользователь запросил tomorrow, предложим кнопку перейти на today
        if day == 'tomorrow':
            kb.add(types.InlineKeyboardButton(get_text(lang, 'today_label'), callback_data=f"cmp_run|{comp1}|{q1}|{comp2}|{q2}|today", style="primary"))
        # всегда добавляем кнопку возврата в меню сравнения
        kb.add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data="cmp_back_to_compare_menu", style="danger"))
        await call.message.edit_text(get_text(lang, 'cmp_no_data', comp1=comp1, queue1=q1, comp2=comp2, queue2=q2, date=format_display_date(date_str)), reply_markup=kb)
        return

    def build_offs(rows):
        offs = []
        for r in rows:
            try:
                s = minutes_from_str(r['off_time'])
                e = minutes_from_str(r['on_time'])
                s = max(0, min(s, 1440))
                e = max(0, min(e, 1440))
                if e <= s:
                    e = 1440
                offs.append((s, e))
            except Exception:
                continue
        return merge_intervals(offs)

    merged_offs1 = build_offs(rows1)
    merged_offs2 = build_offs(rows2)
    ons1 = invert_intervals(merged_offs1)
    ons2 = invert_intervals(merged_offs2)
    common = intersect_intervals(ons1, ons2)

    # Filter out one-minute midnight artifacts: (1439,1440)
    common = [ (s,e) for (s,e) in common if not (s == 1439 and e == 1440) and (e - s) > 0 ]

    if not common:
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data="cmp_back_to_compare_menu", style="danger"))
        await call.message.edit_text(get_text(lang, 'cmp_no_common', comp1=comp1, queue1=q1, comp2=comp2, queue2=q2, date=format_display_date(date_str)), reply_markup=kb)
        return

    # Формат вывода: строки с эмодзи
    lines = [f'<tg-emoji emoji-id="5330396907913098490">🟢</tg-emoji> {format_minutes(s)} - <tg-emoji emoji-id="5330017696660599813">🔴</tg-emoji> {format_minutes(e)}' for s, e in common]
    header = get_text(lang, 'cmp_result_header', comp1=comp1, queue1=q1, comp2=comp2, queue2=q2, date=format_display_date(date_str))
    text = f"{header}\n\n" + "\n".join(lines)

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton(get_text(lang, 'cmp_details_button'), callback_data=f"cmp_details|{comp1}|{q1}|{comp2}|{q2}|{day}", style="primary"))
    other_day = 'tomorrow' if day == 'today' else 'today'
    kb.add(types.InlineKeyboardButton(get_text(lang, 'toggle_day_label', day=(get_text(lang, 'tomorrow_label') if other_day == 'tomorrow' else get_text(lang, 'today_label'))),
                                       callback_data=f"cmp_run|{comp1}|{q1}|{comp2}|{q2}|{other_day}", style="primary"))
    if not saved_id:
        kb.add(types.InlineKeyboardButton(get_text(lang, 'cmp_save_button'), callback_data=f"cmp_save|{comp1}|{q1}|{comp2}|{q2}", style="success"))
    else:
        kb.add(types.InlineKeyboardButton(get_text(lang, 'cmp_delete_saved'), callback_data=f"cmp_del|{saved_id}", style="danger"))
    kb.add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data="cmp_back_to_compare_menu", style="danger"))

    await call.message.edit_text(text, reply_markup=kb)


# Details page (shows both original ON-intervals and marks common ones with ✅)
async def show_compare_details(call: types.CallbackQuery, comp1, q1, comp2, q2, day, lang):
    now = datetime.now(UA_TZ)
    if day == 'tomorrow':
        target_date = (now + timedelta(days=1)).date()
    else:
        target_date = now.date()
    date_str = target_date.strftime('%Y-%m-%d')

    with get_db() as conn:
        rows1 = conn.execute("SELECT off_time, on_time FROM schedules WHERE company=? AND queue=? AND date=?", (comp1, q1, date_str)).fetchall()
        rows2 = conn.execute("SELECT off_time, on_time FROM schedules WHERE company=? AND queue=? AND date=?", (comp2, q2, date_str)).fetchall()

    if not rows1 or not rows2:
        kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data=f"cmp_run|{comp1}|{q1}|{comp2}|{q2}|{day}", style="danger"))
        await call.message.edit_text(get_text(lang, 'cmp_no_data', comp1=comp1, queue1=q1, comp2=comp2, queue2=q2, date=format_display_date(date_str)), reply_markup=kb)
        return

    def build_ons(rows):
        offs = []
        for r in rows:
            try:
                s = minutes_from_str(r['off_time'])
                e = minutes_from_str(r['on_time'])
                s = max(0, min(s, 1440))
                e = max(0, min(e, 1440))
                if e <= s:
                    e = 1440
                offs.append((s, e))
            except Exception:
                continue
        merged_offs = merge_intervals(offs)
        ons = invert_intervals(merged_offs)
        return ons

    ons1 = build_ons(rows1)
    ons2 = build_ons(rows2)
    common = intersect_intervals(ons1, ons2)
    common = [ (s,e) for (s,e) in common if not (s == 1439 and e == 1440) and (e - s) > 0 ]

    def mark_ons(rows, common_intervals, lang):
        offs = []
        for r in rows:
            try:
                s = minutes_from_str(r['off_time'])
                e = minutes_from_str(r['on_time'])
                s = max(0, min(s, 1440))
                e = max(0, min(e, 1440))
                if e <= s:
                    e = 1440
                offs.append((s, e))
            except Exception:
                continue
    
        merged_offs = merge_intervals(offs)
        ons = invert_intervals(merged_offs, 1440)
    
        lines = []
        for s, e in ons:
            is_common = any(not (e <= cs or s >= ce) for cs, ce in common_intervals)
            prefix = "" if is_common else ""
            lines.append(f'{prefix}<tg-emoji emoji-id="5330396907913098490">🟢</tg-emoji> {format_minutes(s)} - <tg-emoji emoji-id="5330017696660599813">🔴</tg-emoji> {format_minutes(e)}')
    
        if not lines:
            return get_text(lang, 'no_schedule_short')
    
        return "\n".join(lines)

    left = mark_ons(rows1, common, lang)
    right = mark_ons(rows2, common, lang)

    header = get_text(lang, 'cmp_details_header', comp1=comp1, queue1=q1, comp2=comp2, queue2=q2, date=format_display_date(date_str))
    text = f"{header}\n\n{get_text(lang, 'cmp_original_1', comp=comp1, queue=q1)}\n{left}\n\n{get_text(lang, 'cmp_original_2', comp=comp2, queue=q2)}\n{right}"

    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data=f"cmp_run|{comp1}|{q1}|{comp2}|{q2}|{day}", style="danger"))
    await call.message.edit_text(text, reply_markup=kb)

async def show_main_menu_msg(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    try:
        await message.answer(get_text(lang, 'menu_main'), reply_markup=main_menu_kb(lang))
    except Exception:
        await message.answer(get_text(lang, 'menu_main'))

def get_user_lang(user_id):
    with get_db() as conn:
        res = conn.execute("SELECT language FROM user_prefs WHERE user_id = ?", (user_id,)).fetchone()
        return res['language'] if res else 'uk'

def lang_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🇺🇦 Українська", callback_data=cb_lang.new(code="uk"), style="primary"),
           types.InlineKeyboardButton("🇷🇺 Русский", callback_data=cb_lang.new(code="ru"), style="primary"))
    return kb

def main_menu_kb(lang):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(get_text(lang, 'btn_add_queue'), get_text(lang, 'btn_my_queues'))
    kb.row(get_text(lang, 'btn_schedules'), get_text(lang, 'btn_compare'))
    kb.row(get_text(lang, 'btn_settings'), get_text(lang, 'btn_support'))
    return kb

def queues_kb(action_type, company, lang):
    queues = ["1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "4.1", "4.2", "5.1", "5.2", "6.1", "6.2"]
    kb = types.InlineKeyboardMarkup(row_width=3)
    btns = []
    
    # Получаем текущую дату для инициализации кнопок просмотра
    today_str = datetime.now(UA_TZ).strftime('%Y-%m-%d')
    
    for q in queues:
        if action_type == 'view':
            # Передаем дату в колбэк
            btns.append(types.InlineKeyboardButton(q, callback_data=cb_sched.new(comp=company, queue=q, date=today_str), style="primary"))
        else:
            btns.append(types.InlineKeyboardButton(q, callback_data=cb_menu.new(action='save', val=f"{company}_{q}"), style="primary"))
    kb.add(*btns)
    back_call = "back_view" if action_type == 'view' else "back_sub"
    kb.add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data=back_call, style="danger"))
    return kb

# --- Обработчики ---
async def check_time_cmd(message: types.Message):
    now = datetime.now(UA_TZ).strftime('%d.%m.%Y %H:%M:%S')
    await message.answer(f"Server time (Europe/Kyiv): {now}")

async def start_cmd(message: types.Message):
    await message.answer(get_text('uk', 'select_lang'), reply_markup=lang_kb())

async def set_language(call: types.CallbackQuery, callback_data: dict):
    lang = callback_data['code']
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO user_prefs (user_id, language) VALUES (?, ?)", (call.from_user.id, lang))
        conn.commit()
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(get_text(lang, 'sub_btn'), url=config.CHANNEL_URL, style="primary")).add(types.InlineKeyboardButton(get_text(lang, 'continue_btn'), callback_data="menu_start", style="success"))
    try:
        await call.message.edit_text(get_text(lang, 'lang_set'))
    except Exception:
        await call.message.answer(get_text(lang, 'lang_set'))
    await call.message.answer(get_text(lang, 'sub_recommend'), reply_markup=kb, disable_web_page_preview=True)
    await call.answer()

async def show_main_menu(call: types.CallbackQuery):
    lang = get_user_lang(call.from_user.id)
    await call.message.answer(get_text(lang, 'menu_main'), reply_markup=main_menu_kb(lang))
    await call.answer()

async def view_schedules_start(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("ДТЕК", callback_data="vcomp_ДТЕК", style="primary"), types.InlineKeyboardButton("ЦЕК", callback_data="vcomp_ЦЕК", style="primary"))
    await message.answer(get_text(lang, 'choose_comp'), reply_markup=kb)

async def add_queue_btn(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    kb = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("ДТЕК", callback_data="scomp_ДТЕК", style="primary"), types.InlineKeyboardButton("ЦЕК", callback_data="scomp_ЦЕК", style="primary"))
    await message.answer(get_text(lang, 'choose_comp'), reply_markup=kb)

async def handle_comp_selection(call: types.CallbackQuery):
    lang = get_user_lang(call.from_user.id)
    try:
        action, comp = call.data.split("_", 1)
    except Exception:
        await call.answer("Невірні дані", show_alert=True)
        return
    mode = 'view' if action == 'vcomp' else 'save'
    await call.message.edit_text(get_text(lang, 'choose_queue', company=comp), reply_markup=queues_kb(mode, comp, lang))
    await call.answer()

async def back_to_comp(call: types.CallbackQuery):
    lang = get_user_lang(call.from_user.id)
    is_view = "view" in call.data
    prefix = "vcomp_" if is_view else "scomp_"
    kb = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("ДТЕК", callback_data=f"{prefix}ДТЕК", style="primary"),
        types.InlineKeyboardButton("ЦЕК", callback_data=f"{prefix}ЦЕК", style="primary")
    )
    await call.message.edit_text(get_text(lang, 'choose_comp'), reply_markup=kb)
    await call.answer()

async def save_sub(call: types.CallbackQuery, callback_data: dict, scheduler):
    lang = get_user_lang(call.from_user.id)
    val = callback_data['val'].split("_")
    comp, q = val[0], val[1]
    
    with get_db() as conn:
        try:
            check = conn.execute(
                "SELECT id FROM users WHERE user_id = ? AND company = ? AND queue = ?", 
                (call.from_user.id, comp, q)
            ).fetchone()
            
            if check:
                await call.answer(get_text(lang, 'exists'), show_alert=True)
                return

            conn.execute(
                "INSERT INTO users (user_id, company, queue) VALUES (?, ?, ?)", 
                (call.from_user.id, comp, q)
            )
            conn.commit()
            
            msg_text = get_text(lang, 'added').format(company=comp, queue=q)
            await call.answer(msg_text, show_alert=True)
            
            # --- Правильное обновление планировщика ---
            from services.scheduler import rebuild_jobs
            await rebuild_jobs(call.bot, scheduler)
            
        except Exception as e:
            print(f"Database error: {e}")
            await call.answer(get_text(lang, 'exists'), show_alert=True)

def format_remaining_time(minutes, lang):
    hours = minutes // 60
    mins = minutes % 60

    parts = []

    if hours > 0:
        if lang == "ru":
            parts.append(f"{hours} ч.")
        else:
            parts.append(f"{hours} год.")

    if mins > 0:
        if lang == "ru":
            parts.append(f"{mins} мин.")
        else:
            parts.append(f"{mins} хв.")

    return " ".join(parts)


def get_status_line(outages, now_time, lang):
    now_minutes = minutes_from_str(now_time)

    for off, on in outages:
        off_m = minutes_from_str(off)
        on_m = minutes_from_str(on)

        if off_m <= now_minutes < on_m:
            remain = on_m - now_minutes
            remain_text = format_remaining_time(remain, lang)

            return get_text(
                lang,
                'status_no_light_until',
                time=on,
                remain=remain_text
            )

    for off, on in outages:
        off_m = minutes_from_str(off)

        if now_minutes < off_m:
            remain = off_m - now_minutes
            remain_text = format_remaining_time(remain, lang)

            return get_text(
                lang,
                'status_light_until',
                time=off,
                remain=remain_text
            )

    return get_text(lang, 'status_light_now')

# Обновленная функция просмотра графиков с кнопками Сегодня/Завтра
async def show_sched(call: types.CallbackQuery, callback_data: dict):
    comp, q = callback_data['comp'], callback_data['queue']
    target_date_str = callback_data.get('date')
    lang = get_user_lang(call.from_user.id)

    now_ua = datetime.now(UA_TZ)
    today_str = now_ua.strftime('%Y-%m-%d')
    tomorrow_str = (now_ua + timedelta(days=1)).strftime('%Y-%m-%d')

    db_date_str = target_date_str or today_str
    display_date_str = format_display_date(db_date_str)

    # --- ЗЧИТУЄМО СТАН АВАРІЙНИХ ВІДКЛЮЧЕНЬ ---
    avaron_mode = False
    with get_db() as conn:
        try:
            res = conn.execute("SELECT value FROM bot_settings WHERE key='avaron'").fetchone()
            if res and res['value'] == '1':
                avaron_mode = True
        except Exception:
            pass

    avar_text = f"\n\n{get_text(lang, 'avar_warning')}" if avaron_mode else ""
    # ------------------------------------------

    with get_db() as conn:
        rows = conn.execute(
            "SELECT off_time, on_time, created_at FROM schedules WHERE company=? AND queue=? AND date=?",
            (comp, q, db_date_str)
        ).fetchall()

    kb = types.InlineKeyboardMarkup(row_width=1)

    # --- НЕТ ДАННЫХ ---
    if not rows:
        schedule_text = f"""<tg-emoji emoji-id="5258105663359294787">🗓</tg-emoji> {get_text(lang,'schedule_title',company=comp,queue=q,date=display_date_str)}

{get_text(lang,'schedule_not_loaded')}{avar_text}

{get_text(lang,'monitor_link')}
"""

    # --- НЕТ ОТКЛЮЧЕНИЙ ---
    elif rows[0]['off_time'] == 'empty':
        updated_at = format_display_datetime(rows[0]['created_at']).replace(' ', ' о ', 1)

        schedule_text = f"""<tg-emoji emoji-id="5258105663359294787">🗓</tg-emoji> {get_text(lang,'schedule_title',company=comp,queue=q,date=display_date_str)}

{get_text(lang,'no_outages_today')}{avar_text}

<i>{get_text(lang,'updated')} {updated_at}</i>

{get_text(lang,'monitor_link')}
"""

    # --- ЕСТЬ ОТКЛЮЧЕНИЯ ---
    else:
        outage_rows = [r for r in rows if r['off_time'] != 'empty']

        outages = []
        lines = []
        total_no_light_minutes = 0

        for row in outage_rows:
            off_minutes = minutes_from_str(row['off_time'])
            on_minutes = minutes_from_str(row['on_time'])

            duration_minutes = max(0, on_minutes - off_minutes)
            total_no_light_minutes += duration_minutes

            outages.append((row['off_time'], row['on_time']))

            duration_text = get_text(
                lang,
                'schedule_hours_value',
                value=_format_hours_decimal(duration_minutes)
            )

            lines.append(
                f"""<tg-emoji emoji-id="6019346268197759615">🔌</tg-emoji> {row['off_time']} - {row['on_time']} <i>({duration_text})</i>"""
            )

        schedule_body = "\n".join(lines)

        total_light_minutes = max(0, 24*60 - total_no_light_minutes)

        total_light = get_text(
            lang,
            'schedule_hours_value',
            value=_format_hours_decimal(total_light_minutes)
        )

        total_no_light = get_text(
            lang,
            'schedule_hours_value',
            value=_format_hours_decimal(total_no_light_minutes)
        )

        updated_at = format_display_datetime(rows[0]['created_at']).replace(' ', ' о ', 1)
        now_time = now_ua.strftime("%H:%M")
        status_line = get_status_line(outages, now_time, lang)

        schedule_text = f"""<tg-emoji emoji-id="5258105663359294787">🗓</tg-emoji> {get_text(lang,'schedule_title',company=comp,queue=q,date=display_date_str)}

{status_line}

{get_text(lang,'section_outages')}
{schedule_body}

{get_text(lang,'section_stats')}
{get_text(lang,'stats_light',value=total_light)}
{get_text(lang,'stats_no_light',value=total_no_light)}{avar_text}

<i>{get_text(lang,'updated')} {updated_at}</i>

{get_text(lang,'monitor_link')}
"""

    # --- КНОПКИ ---
    if db_date_str == today_str:
        kb.add(
            types.InlineKeyboardButton(
                get_text(lang,'tomorrow_label'),
                callback_data=cb_sched.new(comp=comp,queue=q,date=tomorrow_str),
                style="primary"
            )
        )
    else:
        kb.add(
            types.InlineKeyboardButton(
                get_text(lang,'today_label'),
                callback_data=cb_sched.new(comp=comp,queue=q,date=today_str),
                style="primary"
            )
        )

    kb.add(
        types.InlineKeyboardButton(
            get_text(lang,'back'),
            callback_data=f"vcomp_{comp}",
            style="danger"
        )
    )

    try:
        await call.message.edit_text(
            schedule_text,
            reply_markup=kb,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception:
        await call.answer()

    await call.answer()

async def my_queues(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    with get_db() as conn:
        rows = conn.execute("SELECT id, company, queue FROM users WHERE user_id=?", (message.from_user.id,)).fetchall()
    if not rows:
        return await message.answer(get_text(lang, 'empty_list'))
    kb = types.InlineKeyboardMarkup()
    for r in rows:
        kb.add(types.InlineKeyboardButton(f"🗑 {r['company']} {r['queue']}", callback_data=f"del_{r['id']}", style="danger"))
    await message.answer(get_text(lang, 'my_que'), reply_markup=kb)

async def delete_sub(call: types.CallbackQuery, scheduler):
    # 1. Определяем язык пользователя
    lang = get_user_lang(call.from_user.id)
    
    try:
        # Извлекаем ID строки из callback_data (например, 'del_5' -> '5')
        sub_id = call.data.split("_", 1)[1]
    except Exception:
        msg = get_text(lang, "invalid_data") if get_text else "Невірні дані"
        await call.answer(msg, show_alert=True)
        return

    # 2. Удаляем подписку из БД
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE id=?", (sub_id,))
        conn.commit()

    # Всплывающее уведомление
    await call.answer(get_text(lang, 'deleted'), show_alert=False)

    # 3. Обновляем планировщик уведомлений
    try:
        from services.scheduler import rebuild_jobs
        await rebuild_jobs(call.bot, scheduler)
    except Exception as e:
        print(f"Failed to rebuild scheduler: {e}")

    # 4. ФОРМИРУЕМ ОБНОВЛЕННОЕ МЕНЮ
    with get_db() as conn:
        # Получаем актуальный список черг пользователя
        rows = conn.execute(
            "SELECT id, company, queue FROM users WHERE user_id=?", 
            (call.from_user.id,)
        ).fetchall()

    if not rows:
        # Если черг больше нет
        new_text = get_text(lang, 'empty_list')
        new_kb = None # Или можно добавить кнопку "Назад"
    else:
        # Если черги остались — создаем новую клавиатуру
        new_text = get_text(lang, 'my_que')
        new_kb = types.InlineKeyboardMarkup()
        for r in rows:
            # Создаем кнопки заново с актуальными ID
            new_kb.add(types.InlineKeyboardButton(
                f"🗑 {r['company']} {r['queue']}", 
                callback_data=f"del_{r['id']}"
            ))

    # 5. Редактируем текущее сообщение (Бесшовное обновление)
    try:
        await call.message.edit_text(
            text=new_text, 
            reply_markup=new_kb, 
            parse_mode='HTML'
        )
    except Exception as e:
        # Если текст не изменился, Telegram выдаст ошибку, просто игнорируем её
        pass

async def support_cmd(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    await message.answer(get_text(lang, 'support_text', user=config.SUPPORT_USER, url=config.DONATE_URL), disable_web_page_preview=True, parse_mode=types.ParseMode.HTML)

async def settings_cmd(message: types.Message):
    lang = get_user_lang(message.from_user.id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(get_text(lang, 'btn_lang_switch'), callback_data="open_lang", style="primary"))
    kb.add(types.InlineKeyboardButton(get_text(lang, 'btn_notifications'), callback_data="open_notifications", style="primary"))
    kb.add(types.InlineKeyboardButton(get_text(lang, 'btn_toggle_all'), callback_data="toggle_all", style="danger"))
    await message.answer(get_text(lang, 'settings_text'), reply_markup=kb)

async def open_language_menu(call: types.CallbackQuery):
    lang = get_user_lang(call.from_user.id)
    try:
        await call.message.answer(get_text(lang, 'select_lang'), reply_markup=lang_kb())
    except Exception:
        try:
            await call.message.edit_text(get_text(lang, 'select_lang'), reply_markup=lang_kb())
        except Exception:
            pass
    await call.answer()

async def open_notifications(call: types.CallbackQuery):
    user_id = call.from_user.id
    settings = get_user_settings(user_id)
    lang = settings['language']

    def state_emoji(v): return "✅" if int(v) == 1 else "❌"

    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(f"{get_text(lang, 'notif_label_off')}: {state_emoji(settings['notify_off'])}", callback_data=cb_notify.new(key='notify_off', val=settings['notify_off']), style="danger"))
    kb.add(types.InlineKeyboardButton(f"{get_text(lang, 'notif_label_on')}: {state_emoji(settings['notify_on'])}", callback_data=cb_notify.new(key='notify_on', val=settings['notify_on']), style="danger"))
    kb.add(types.InlineKeyboardButton(f"{get_text(lang, 'notif_label_off_10')}: {state_emoji(settings['notify_off_10'])}", callback_data=cb_notify.new(key='notify_off_10', val=settings['notify_off_10']), style="danger"))
    kb.add(types.InlineKeyboardButton(f"{get_text(lang, 'notif_label_on_10')}: {state_emoji(settings['notify_on_10'])}", callback_data=cb_notify.new(key='notify_on_10', val=settings['notify_on_10']), style="danger"))
    kb.add(types.InlineKeyboardButton(get_text(lang, 'back'), callback_data="open_settings_back"))
    try:
        await call.message.edit_text(get_text(lang, 'notifications_text'), reply_markup=kb)
    except Exception:
        await call.message.answer(get_text(lang, 'notifications_text'), reply_markup=kb)
    await call.answer()

async def toggle_notify(call: types.CallbackQuery, callback_data: dict):
    user_id = call.from_user.id
    key = callback_data['key']
    try:
        current = int(callback_data['val'])
    except Exception:
        current = get_user_settings(user_id).get(key, 1)
    new = 0 if current == 1 else 1
    set_user_setting(user_id, key, new)
    await open_notifications(call)

async def toggle_all_notify(call: types.CallbackQuery):
    user_id = call.from_user.id
    settings = get_user_settings(user_id)
    any_enabled = any([settings['notify_off'], settings['notify_on'], settings['notify_off_10'], settings['notify_on_10']])
    new = 0 if any_enabled else 1
    for k in ['notify_off', 'notify_on', 'notify_off_10', 'notify_on_10']:
        set_user_setting(user_id, k, new)
    lang = get_user_lang(user_id)
    state_text = "ON" if new == 1 else "OFF"
    try:
        await call.answer(get_text(lang, 'notif_all_set', state=state_text), show_alert=False)
    except Exception:
        await call.answer("OK", show_alert=False)
    await open_notifications(call)

async def back_to_settings_from_notifications(call: types.CallbackQuery):
    lang = get_user_lang(call.from_user.id)
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(get_text(lang, 'btn_lang_switch'), callback_data="open_lang", style="primary"))
    kb.add(types.InlineKeyboardButton(get_text(lang, 'btn_notifications'), callback_data="open_notifications", style="primary"))
    kb.add(types.InlineKeyboardButton(get_text(lang, 'btn_toggle_all'), callback_data="toggle_all", style="danger"))
    try:
        await call.message.edit_text(get_text(lang, 'settings_text'), reply_markup=kb)
    except Exception:
        await call.message.answer(get_text(lang, 'settings_text'), reply_markup=kb)
    await call.answer()

async def inline_echo(inline_query: types.InlineQuery):
    query_text = inline_query.query.strip().lower()
    if not query_text:
        return

    parts = query_text.split()
    if len(parts) < 2:
        return

    company = parts[0].upper().replace('DTEK', 'ДТЕК')
    queue = parts[1]

    now_ua = datetime.now(UA_TZ)
    today_dt = now_ua
    tomorrow_dt = now_ua + timedelta(days=1)

    today_db = today_dt.strftime('%Y-%m-%d')
    tomorrow_db = tomorrow_dt.strftime('%Y-%m-%d')

    target_date_db = today_db
    display_date = today_dt.strftime('%d.%m.%Y')
    day_label = "на сьогодні"

    if 'завтра' in query_text:
        target_date_db = tomorrow_db
        display_date = tomorrow_dt.strftime('%d.%m.%Y')
        day_label = "на завтра"
    elif any(word in query_text for word in ['сегодня', 'сьогодні', 'сьогодня']):
        target_date_db = today_db
        display_date = today_dt.strftime('%d.%m.%Y')
        day_label = "на сьогодні"

    with get_db() as conn:
        rows = conn.execute(
            "SELECT off_time, on_time FROM schedules WHERE company=? AND queue=? AND date=?",
            (company, queue, target_date_db)
        ).fetchall()

    if not rows:
        schedule_text = "\n❗️ На жаль, графік для цієї черги на обрану дату ще не завантажено."
    elif rows[0]['off_time'] == 'empty':
        schedule_text = "\n✅ <b>Відключень не планується!</b> 🎉"
    else:
        total_off_minutes = 0
        lines = []

        for r in rows:
            off_time = r['off_time']
            on_time = r['on_time']

            off_dt = datetime.strptime(off_time, "%H:%M")
            on_dt = datetime.strptime(on_time, "%H:%M")

            # переход через 00:00
            if on_dt <= off_dt:
                on_dt += timedelta(days=1)

            # 23:59 считаем как 24:00
            if on_time == "23:59":
                on_dt += timedelta(minutes=1)

            diff = on_dt - off_dt
            minutes = int(diff.total_seconds() // 60)
            total_off_minutes += minutes

            # округление до 0.5 часа
            hours_float = minutes / 60
            hours_float = round(hours_float * 2) / 2

            if hours_float.is_integer():
                hours_str = str(int(hours_float))
            else:
                hours_str = str(hours_float)

            lines.append(
                f"""🔌 {off_time} - {on_time} <i>({hours_str} год.)</i>"""
            )

        # итог по суткам
        total_hours_float = total_off_minutes / 60
        total_hours_float = round(total_hours_float * 2) / 2

        if total_hours_float.is_integer():
            total_off_str = str(int(total_hours_float))
        else:
            total_off_str = str(total_hours_float)

        total_on_float = 24 - total_hours_float

        if total_on_float.is_integer():
            total_on_str = str(int(total_on_float))
        else:
            total_on_str = str(total_on_float)

        schedule_text = (
            "\n"
            + "\n".join(lines)
            + "\n\n"
            + f"✅ <b>Зі світлом:</b> {total_on_str} год.\n"
            + f"❌ <b>Без світла:</b> {total_off_str} год."
        )

    result_text = (
        f"<b>📅 Графік {company} {queue} на {display_date}:</b>\n"
        f"{schedule_text}\n\n"
        f"💡 <a href='https://t.me/lightmeuaBot'><b>Монітор світла</b></a>"
    )

    item = types.InlineQueryResultArticle(
        id=str(uuid.uuid4()),
        title=f"Графік {company} {queue} ({day_label})",
        description="Натисніть, щоб відправити графік у чат",
        input_message_content=types.InputTextMessageContent(
            message_text=result_text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    )

    await inline_query.answer(results=[item], cache_time=60)

# --- Реєстрація ---
def register_handlers(dp: Dispatcher, scheduler): # <-- Добавили scheduler
    dp.register_message_handler(compare_menu, lambda m: bool(m.text) and m.text == get_text(get_user_lang(m.from_user.id), 'btn_compare'))
    dp.register_message_handler(compare_new_start, lambda m: bool(m.text) and m.text == get_text(get_user_lang(m.from_user.id), 'btn_compare_new'))
    dp.register_message_handler(compare_my_list, lambda m: bool(m.text) and m.text == get_text(get_user_lang(m.from_user.id), 'btn_compare_my'))

    dp.register_callback_query_handler(
        compare_callback_router,
        lambda c: c.data and any(c.data.startswith(p) for p in (
            'cmp_back','cmp_c1|','cmp_q1|','cmp_c2|','cmp_q2|','cmp_run|','cmp_save|','cmp_run_saved|','cmp_del|','cmp_details|'
        ))
    )

    back_labels = (get_text('uk', 'back'), get_text('ru', 'back'))
    dp.register_message_handler(
        show_main_menu_msg,
        lambda m: (m.reply_to_message is None) and bool(m.text) and (m.text in back_labels)
    )
    
    dp.register_message_handler(check_time_cmd, commands=['check'])
    dp.register_message_handler(start_cmd, commands=['start'])
    dp.register_callback_query_handler(set_language, cb_lang.filter())
    dp.register_callback_query_handler(show_main_menu, text="menu_start")

    dp.register_message_handler(view_schedules_start, lambda m: bool(m.text) and any(x in m.text.lower() for x in ["графік", "график"]))
    dp.register_message_handler(add_queue_btn, lambda m: bool(m.text) and any(x in m.text.lower() for x in ["додати", "добавить"]))
    dp.register_message_handler(my_queues, lambda m: bool(m.text) and any(x in m.text.lower() for x in ["мої чер", "мои оче"]))

    support_labels = (get_text('uk', 'btn_support'), get_text('ru', 'btn_support'))
    settings_labels = (get_text('uk', 'btn_settings'), get_text('ru', 'btn_settings'))
    dp.register_message_handler(support_cmd, lambda m: bool(m.text) and m.text in support_labels)
    dp.register_message_handler(settings_cmd, lambda m: bool(m.text) and m.text in settings_labels)

    dp.register_callback_query_handler(handle_comp_selection, lambda c: c.data and c.data.startswith(('vcomp_', 'scomp_')))
    dp.register_callback_query_handler(show_sched, cb_sched.filter())
    
    async def _save_sub_wrapper(call: types.CallbackQuery, callback_data: dict):
        await save_sub(call, callback_data, scheduler)
    dp.register_callback_query_handler(_save_sub_wrapper, cb_menu.filter(action="save"))
    
    dp.register_callback_query_handler(open_language_menu, text="open_lang")

    dp.register_callback_query_handler(open_notifications, text="open_notifications")
    dp.register_callback_query_handler(toggle_notify, cb_notify.filter())
    dp.register_callback_query_handler(toggle_all_notify, text="toggle_all")
    dp.register_callback_query_handler(back_to_settings_from_notifications, text="open_settings_back")

    dp.register_callback_query_handler(back_to_comp, text=["back_view", "back_sub"])
    
    async def _delete_sub_wrapper(call: types.CallbackQuery):
        await delete_sub(call, scheduler)
    dp.register_callback_query_handler(_delete_sub_wrapper, lambda c: c.data and c.data.startswith('del_'))

    dp.register_message_handler(view_schedules_start, commands=['sched'])
    dp.register_message_handler(add_queue_btn, commands=['add'])
    dp.register_message_handler(my_queues, commands=['subs'])
    dp.register_message_handler(show_main_menu_msg, commands=['menu'])
    dp.register_message_handler(support_cmd, commands=['support'])
    dp.register_message_handler(settings_cmd, commands=['settings'])
    dp.register_message_handler(compare_menu, commands=['compare'])
  
    dp.register_inline_handler(inline_echo)



























