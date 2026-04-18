from aiogram import Bot
import pytz
from datetime import datetime, timedelta
from database.db import get_db
from locales.strings import get_text

UA_TZ = pytz.timezone('Europe/Kyiv')

def format_duration(start_dt, end_dt, lang):
    delta = end_dt - start_dt
    total_seconds = int(delta.total_seconds())
    if total_seconds < 0:
        total_seconds = 0

    minutes = total_seconds // 60
    hours_unit = get_text(lang, 'units_hours')
    mins_unit = get_text(lang, 'units_minutes')
    if minutes < 60:
        return f"{minutes} {mins_unit}"
    else:
        hours = minutes / 60
        if hours % 1 == 0:
            return f"{int(hours)} {hours_unit}"

        return f"{round(hours, 1)} {hours_unit}"

def get_next_off_event(company, queue, current_date_obj, current_time_str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT date, off_time FROM schedules "
            "WHERE company=? AND queue=? AND date=? AND off_time > ? "
            "ORDER BY off_time ASC LIMIT 1",
            (company, queue, current_date_obj.strftime('%Y-%m-%d'), current_time_str)
        ).fetchone()

    if row:
        return parse_localized_datetime(row['date'], row['off_time'])
    next_date_str = (current_date_obj + timedelta(days=1)).strftime('%Y-%m-%d')

    with get_db() as conn:
        row_next = conn.execute(
            "SELECT date, off_time FROM schedules "
            "WHERE company=? AND queue=? AND date=? "
            "ORDER BY off_time ASC LIMIT 1",
            (company, queue, next_date_str)
        ).fetchone()

    if row_next:
        return parse_localized_datetime(row_next['date'], row_next['off_time'])

    return None

def get_effective_on_event(company, queue, date_obj, on_time_str):
    effective_on_dt = parse_localized_datetime(date_obj.strftime('%Y-%m-%d'), on_time_str)
    current_date = date_obj
    for _ in range(7):
        if normalized_time_key(effective_on_dt.strftime('%H:%M')) not in ('23:59', '00:00'):
            break
        next_date_str = (current_date + timedelta(days=1)).strftime('%Y-%m-%d')
        with get_db() as conn:
            next_row = conn.execute(
                "SELECT date, on_time FROM schedules "
                "WHERE company=? AND queue=? AND date=? AND off_time='00:00' "
                "ORDER BY on_time ASC LIMIT 1",
                (company, queue, next_date_str)
            ).fetchone()
        if not next_row:
            break

        effective_on_dt = parse_localized_datetime(next_row['date'], next_row['on_time'])
        current_date = datetime.strptime(next_row['date'], '%Y-%m-%d').date()

    return effective_on_dt

async def send_reminder(bot: Bot, user_id, company, queue, action, lang, next_event_str=None, duration_str=None, current_event_time_str=None):
    if action in ('off_now', 'on_now') and next_event_str and duration_str:
        key = f'{action}_extended'
        text = get_text(lang, key, company=company, queue=queue, time=current_event_time_str, next_time=next_event_str, duration=duration_str)
    elif action in ('off', 'on'):
        key = f'reminder_{action}'
        text = get_text(lang, key, company=company, queue=queue)
    else:
        key = action
        text = get_text(lang, key, company=company, queue=queue)
    try:
        await bot.send_message(user_id, text)
    except Exception as e:
        print(f"Ошибка отправки напоминания {user_id}: {e}")

def normalize_time_and_offset(time_str: str):
    t = time_str.strip()
    if t == '24:00':
        return '00:00', 1

    return t, 0

def parse_localized_datetime(date_str: str, time_str: str):
    norm_time, day_off = normalize_time_and_offset(time_str)
    dt_naive = datetime.strptime(f"{date_str} {norm_time}", '%Y-%m-%d %H:%M')
    dt = dt_naive + timedelta(days=day_off)

    return UA_TZ.localize(dt)

def normalized_time_key(time_str: str):
    norm, _ = normalize_time_and_offset(time_str)

    return norm

async def rebuild_jobs(bot, scheduler):
    try:
        scheduler.remove_all_jobs()
    except Exception:
        pass

    now_ua = datetime.now(UA_TZ)
    with get_db() as conn:
        rows = conn.execute("SELECT company, queue, date, off_time, on_time FROM schedules").fetchall()

    for sched in rows:
        try:
            company = sched['company']
            queue = sched['queue']
            date_str = sched['date']
            off_time_str = sched['off_time']
            on_time_str = sched['on_time']
            try:
                off_t = parse_localized_datetime(date_str, off_time_str)
            except Exception as e:
                continue
            try:
                on_t = parse_localized_datetime(date_str, on_time_str)
            except Exception as e:
                continue

            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            skip_on_due_to_next_day = False

            if normalized_time_key(on_time_str) in ('23:59', '00:00'):
                next_date_str = (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
                with get_db() as conn:
                    next_rows = conn.execute("SELECT off_time FROM schedules WHERE company=? AND queue=? AND date=?", (company, queue, next_date_str)).fetchall()
                for nr in next_rows:
                    if normalized_time_key(nr['off_time']) == '00:00':
                        skip_on_due_to_next_day = True
                        break

            skip_off_due_to_prev_day = False
            if normalized_time_key(off_time_str) == '00:00':
                prev_date_str = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
                with get_db() as conn:
                    prev_rows = conn.execute("SELECT on_time FROM schedules WHERE company=? AND queue=? AND date=?", (company, queue, prev_date_str)).fetchall()
                for pr in prev_rows:
                    if normalized_time_key(pr['on_time']) in ('23:59', '00:00'):
                        skip_off_due_to_prev_day = True
                        break

            with get_db() as conn:
                users = conn.execute(
                    "SELECT u.user_id, COALESCE(p.language, 'uk') as language, "
                    "COALESCE(p.notify_off, 1) as notify_off, COALESCE(p.notify_on, 1) as notify_on, "
                    "COALESCE(p.notify_off_10, 1) as notify_off_10, COALESCE(p.notify_on_10, 1) as notify_on_10 "
                    "FROM users u LEFT JOIN user_prefs p ON u.user_id = p.user_id "
                    "WHERE u.company=? AND u.queue=?",
                    (company, queue)
                ).fetchall()

            for user in users:
                user_id = user['user_id']
                lang = user['language'] or 'uk'
                if not skip_off_due_to_prev_day:
                    rem_off = off_t - timedelta(minutes=10)
                    if rem_off > now_ua and int(user['notify_off_10']) == 1:
                        scheduler.add_job(send_reminder, 'date', run_date=rem_off, args=[bot, user_id, company, queue, 'off', lang])
                    if off_t > now_ua and int(user['notify_off']) == 1:
                        effective_on_t = get_effective_on_event(company, queue, date_obj, on_time_str)
                        next_on_time_str = effective_on_t.strftime('%H:%M')
                        duration_str = format_duration(off_t, effective_on_t, lang)
                        current_time_str = off_t.strftime('%H:%M')
                        scheduler.add_job(send_reminder, 'date', run_date=off_t, args=[bot, user_id, company, queue, 'off_now', lang, next_on_time_str, duration_str, current_time_str])

                if not skip_on_due_to_next_day:
                    rem_on = on_t - timedelta(minutes=10)
                    if rem_on > now_ua and int(user['notify_on_10']) == 1:
                        scheduler.add_job(send_reminder, 'date', run_date=rem_on, args=[bot, user_id, company, queue, 'on', lang])
                    if on_t > now_ua and int(user['notify_on']) == 1:
                        next_off_dt = get_next_off_event(company, queue, date_obj, on_time_str)
                        if next_off_dt:
                            next_off_time_str = next_off_dt.strftime('%H:%M')
                            duration_str = format_duration(on_t, next_off_dt, lang)
                        else:
                            next_off_time_str = "??"
                            duration_str = "??"
                        current_time_str = on_t.strftime('%H:%M')

                        scheduler.add_job(send_reminder, 'date', run_date=on_t, args=[bot, user_id, company, queue, 'on_now', lang, next_off_time_str, duration_str, current_time_str])
        except Exception as e:
            continue
