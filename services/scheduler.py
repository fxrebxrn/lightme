import pytz
from datetime import datetime, timedelta
from database.db import get_db
from locales.strings import get_text

# Принудительная часовая зона
UA_TZ = pytz.timezone('Europe/Kyiv')

def format_duration(start_dt, end_dt, lang):
    """
    Рассчитывает разницу и возвращает красивую строку:
    - "30 минут"
    - "2 часа" (вместо 2.0)
    - "3.5 часа"
    """
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
        # ПЕРЕВІРКА: якщо години цілі (наприклад, 2.0), перетворюємо в int (2)
        if hours % 1 == 0:
            return f"{int(hours)} {hours_unit}"
        # Якщо є дробова частина (наприклад, 2.5), залишаємо один знак після крапки
        return f"{round(hours, 1)} {hours_unit}"

def get_next_off_event(company, queue, current_date_obj, current_time_str):
    """
    Ищет следующее ВЫКЛЮЧЕНИЕ (off_time) после текущего момента.
    Ищет сегодня, а если нет — в начале завтрашнего дня.
    Возвращает datetime или None.
    """
    # 1. Ищем сегодня, где off_time > current_time_str
    # Важно: 24:00 в базе больше чем 23:00, сортировка строк работает корректно
    with get_db() as conn:
        row = conn.execute(
            "SELECT date, off_time FROM schedules "
            "WHERE company=? AND queue=? AND date=? AND off_time > ? "
            "ORDER BY off_time ASC LIMIT 1",
            (company, queue, current_date_obj.strftime('%Y-%m-%d'), current_time_str)
        ).fetchone()
    
    if row:
        return parse_localized_datetime(row['date'], row['off_time'])
    
    # 2. Если сегодня больше нет выключений, ищем ПЕРВОЕ выключение завтра
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
    """
    Возвращает фактическое время ВКЛЮЧЕНИЯ для текущего интервала.

    Если интервал заканчивается около полуночи (23:59/00:00) и на следующий день
    есть интервал с off_time=00:00, считаем это непрерывным отключением и переносим
    время включения на on_time следующего дня.
    """
    effective_on_dt = parse_localized_datetime(date_obj.strftime('%Y-%m-%d'), on_time_str)
    current_date = date_obj

    # Ограничиваем глубину, чтобы защититься от потенциальных циклов в данных.
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

async def send_reminder(bot, user_id, company, queue, action, lang, next_event_str=None, duration_str=None, current_event_time_str=None):
    """Отправляет напоминание пользователю."""
    # action может быть: 'off'/'on' (reminder за 10 минут) или 'off_now'/'on_now' (уведомление в момент события)
    
    # Выбираем ключ текста
    if action in ('off_now', 'on_now') and next_event_str and duration_str:
        # Используем новые расширенные сообщения
        key = f'{action}_extended'
        text = get_text(lang, key, 
                        company=company, 
                        queue=queue, 
                        time=current_event_time_str, # Время текущего события (18:00)
                        next_time=next_event_str,    # Время следующего (22:00)
                        duration=duration_str)       # Длительность (4 часа)
    elif action in ('off', 'on'):
        key = f'reminder_{action}'
        text = get_text(lang, key, company=company, queue=queue)
    else:
        # Фолбек на старые короткие сообщения, если данных нет
        key = action
        text = get_text(lang, key, company=company, queue=queue)

    try:
        await bot.send_message(user_id, text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки напоминания {user_id}: {e}")

def normalize_time_and_offset(time_str: str):
    """
    Нормализует строку времени.
    Возвращает (normalized_time_str, day_offset).
    '24:00' -> ('00:00', 1)
    Иные значения возвращаются как есть с offset 0.
    """
    t = time_str.strip()
    if t == '24:00':
        return '00:00', 1
    return t, 0

def parse_localized_datetime(date_str: str, time_str: str):
    """
    Парсит дату+время и возвращает timezone-aware datetime в UA_TZ.
    Поддерживает '24:00' (как 00:00 следующего дня).
    """
    norm_time, day_off = normalize_time_and_offset(time_str)
    try:
        dt_naive = datetime.strptime(f"{date_str} {norm_time}", '%Y-%m-%d %H:%M')
        dt = dt_naive + timedelta(days=day_off)
        return UA_TZ.localize(dt)
    except Exception as e:
        raise

def normalized_time_key(time_str: str):
    """
    Возвращает нормализованную строку времени для сравнений, '24:00' -> '00:00'.
    """
    norm, _ = normalize_time_and_offset(time_str)
    return norm

async def rebuild_jobs(bot, scheduler):
    """
    Перестраивает все задания планировщика.
    """
    try:
        scheduler.remove_all_jobs()
    except Exception:
        pass

    now_ua = datetime.now(UA_TZ)

    # Получаем все графики
    with get_db() as conn:
        rows = conn.execute(
            "SELECT company, queue, date, off_time, on_time FROM schedules"
        ).fetchall()

    for sched in rows:
        try:
            company = sched['company']
            queue = sched['queue']
            date_str = sched['date']
            off_time_str = sched['off_time']
            on_time_str = sched['on_time']

            # Парсим времена текущей строки
            try:
                off_t = parse_localized_datetime(date_str, off_time_str)
            except Exception as e:
                print(f"Error parsing off datetime: {e}")
                continue
            
            try:
                on_t = parse_localized_datetime(date_str, on_time_str)
            except Exception as e:
                print(f"Error parsing on datetime: {e}")
                continue

            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

            # --- ЛОГИКА СКЛЕЙКИ ---
            
            # 1. Forward Check (Будущее): ON 24:00 -> OFF 00:00 завтра
            skip_on_due_to_next_day = False
            if normalized_time_key(on_time_str) in ('23:59', '00:00'):
                next_date_str = (date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
                with get_db() as conn:
                    next_rows = conn.execute(
                        "SELECT off_time FROM schedules WHERE company=? AND queue=? AND date=?",
                        (company, queue, next_date_str)
                    ).fetchall()
                for nr in next_rows:
                    if normalized_time_key(nr['off_time']) == '00:00':
                        skip_on_due_to_next_day = True
                        break

            # 2. Backward Check (Прошлое): OFF 00:00 <- ON 24:00 вчера
            skip_off_due_to_prev_day = False
            if normalized_time_key(off_time_str) == '00:00':
                prev_date_str = (date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
                with get_db() as conn:
                    prev_rows = conn.execute(
                        "SELECT on_time FROM schedules WHERE company=? AND queue=? AND date=?",
                        (company, queue, prev_date_str)
                    ).fetchall()
                for pr in prev_rows:
                    if normalized_time_key(pr['on_time']) in ('23:59', '00:00'):
                        skip_off_due_to_prev_day = True
                        break
            
            # --- ПОЛУЧАЕМ ПОЛЬЗОВАТЕЛЕЙ ---
            with get_db() as conn:
                users = conn.execute(
                    "SELECT u.user_id, COALESCE(p.language, 'uk') as language, "
                    "COALESCE(p.notify_off, 1) as notify_off, COALESCE(p.notify_on, 1) as notify_on, "
                    "COALESCE(p.notify_off_10, 1) as notify_off_10, COALESCE(p.notify_on_10, 1) as notify_on_10 "
                    "FROM users u LEFT JOIN user_prefs p ON u.user_id = p.user_id "
                    "WHERE u.company=? AND u.queue=?",
                    (company, queue)
                ).fetchall()

            # --- ПЛАНИРОВАНИЕ ЗАДАЧ ---

            for user in users:
                user_id = user['user_id']
                lang = user['language'] or 'uk'

                # 1. Уведомления об ОТКЛЮЧЕНИИ (OFF)
                if not skip_off_due_to_prev_day:
                    # Reminder 10 min
                    rem_off = off_t - timedelta(minutes=10)
                    if rem_off > now_ua and int(user['notify_off_10']) == 1:
                        scheduler.add_job(send_reminder, 'date', run_date=rem_off,
                                          args=[bot, user_id, company, queue, 'off', lang])
                    
                    # OFF NOW Notification
                    if off_t > now_ua and int(user['notify_off']) == 1:
                        # Логика для сообщения "Выключено. Включат через Х"
                        # Следующее включение может быть в следующем дне, если
                        # есть связка 23:59 -> 00:00 (непрерывное отключение).
                        effective_on_t = get_effective_on_event(company, queue, date_obj, on_time_str)
                        next_on_time_str = effective_on_t.strftime('%H:%M')
                        duration_str = format_duration(off_t, effective_on_t, lang)
                        current_time_str = off_t.strftime('%H:%M')

                        scheduler.add_job(send_reminder, 'date', run_date=off_t,
                                          args=[bot, user_id, company, queue, 'off_now', lang, 
                                                next_on_time_str, duration_str, current_time_str])

                # 2. Уведомления о ВКЛЮЧЕНИИ (ON)
                if not skip_on_due_to_next_day:
                    # Reminder 10 min
                    rem_on = on_t - timedelta(minutes=10)
                    if rem_on > now_ua and int(user['notify_on_10']) == 1:
                        scheduler.add_job(send_reminder, 'date', run_date=rem_on,
                                          args=[bot, user_id, company, queue, 'on', lang])
                    
                    # ON NOW Notification
                    if on_t > now_ua and int(user['notify_on']) == 1:
                        # Логика для сообщения "Включено. Выключат через Х"
                        # Следующее выключение - это off_time СЛЕДУЮЩЕЙ строки (или завтра)
                        next_off_dt = get_next_off_event(company, queue, date_obj, on_time_str)
                        
                        if next_off_dt:
                            next_off_time_str = next_off_dt.strftime('%H:%M')
                            duration_str = format_duration(on_t, next_off_dt, lang)
                        else:
                            # Если данных на будущее нет
                            next_off_time_str = "??"
                            duration_str = "??"

                        current_time_str = on_t.strftime('%H:%M')

                        scheduler.add_job(send_reminder, 'date', run_date=on_t,
                                          args=[bot, user_id, company, queue, 'on_now', lang,
                                                next_off_time_str, duration_str, current_time_str])

        except Exception as e:
            print(f"Global error processing schedule row: {e}")

    print(f"✅ Задания планировщика обновлены: {datetime.now(UA_TZ)}")