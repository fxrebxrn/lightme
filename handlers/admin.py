from aiogram import Dispatcher, types
from config import ADMIN_ID
from services.parser import parse_schedule_text
from database.db import get_db
from services.scheduler import rebuild_jobs
from locales.strings import get_text
import asyncio
import config
from database.db import get_stats
import os
import tempfile
import sqlite3
import shutil
from datetime import datetime

def format_display_date(date_str: str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d.%m.%Y')
    except Exception:
        return date_str
        
async def download_db(message: types.Message):
    if message.from_user.id != config.ADMIN_ID:
        return

    db_path = "/app/data/database.db" # Переконайся, що шлях веде до Volume

    if os.path.exists(db_path):
        # Використовуємо open(), щоб правильно передати файл
        with open(db_path, 'rb') as f:
            await message.answer_document(f, caption="📂 База даних з Volume (/app/data)")
    else:
        try:
            content = os.listdir('/app/data')
            await message.answer(f"❌ database.db не знайдено.\nВміст папки data: <code>{', '.join(content) if content else 'ПУСТО'}</code>", parse_mode='HTML')
        except Exception as e:
            await message.answer(f"❌ Помилка доступу до /app/data: {e}")
            
async def upload_db_via_bot(message: types.Message):
    # Только админ может загружать
    if message.from_user.id != config.ADMIN_ID:
        return await message.answer("🚫 Доступ заборонено.")

    doc = message.document
    # Проверка имени
    if doc.file_name != 'database.db':
        return await message.answer("Файл повинен називатися точно <code>database.db</code>.", parse_mode='HTML')

    # Ограничение размера (примерно 50MB)
    MAX_SIZE = 50 * 1024 * 1024
    if doc.file_size and doc.file_size > MAX_SIZE:
        return await message.answer(f"Файл забагато. Максимум {MAX_SIZE // (1024*1024)} MB.")

    # Скачиваем во временный файл
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, prefix="db_upload_", suffix=".db") as tf:
            temp_path = tf.name
        await message.document.download(destination_file=temp_path)
    except Exception as e:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        await message.answer(f"❌ Не вдалося завантажити файл: {e}")
        return

    # Простейшая валидация
    try:
        con = sqlite3.connect(f"file:{temp_path}?mode=ro", uri=True, timeout=5)
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1;")
        _ = cur.fetchone()
        con.close()
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        await message.answer(f"❌ Файл не валідна SQLite база: {e}")
        return

    # Путь к рабочей базе (volume /app/data)
    dst = "/app/data/database.db"
    backup_path = dst + ".bak"

    try:
        # Создаём резервную копию текущей БД (если существует)
        if os.path.exists(dst):
            try:
                # ВАЖНО: Тут тоже используем shutil.move вместо os.replace
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                shutil.move(dst, backup_path)
            except Exception as e:
                print("Warning: cannot create backup of existing DB:", e)

        # Атомично заменяем (ИСПОЛЬЗУЕМ shutil.move!)
        shutil.move(temp_path, dst)
        
        # Даем права на файл (на всякий случай для Docker)
        os.chmod(dst, 0o666)
        
    except Exception as e:
        # попытка отката из backup
        try:
            if os.path.exists(backup_path) and not os.path.exists(dst):
                shutil.move(backup_path, dst)
        except Exception:
            pass
        await message.answer(f"❌ Помилка при заміні бази: {e}")
        return
    finally:
        # Чистим временный файл если он остался
        if temp_path and os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass

    # Уведомляем админа
    await message.answer("✅ Базу успішно замінено. Потрібно перезапустити бота, щоб нова база почала використовуватись.")
        
async def admin_stats(message: types.Message):
    # Перевірка, чи це адмін (додай свій ID у config.py)
    if message.from_user.id != config.ADMIN_ID:
        return

    users_count, subs_count = get_stats()
    
    text = (
        "📊 <b>Статистика бота:</b>\n\n"
        f"👤 Унікальних користувачів: <code>{users_count}</code>\n"
        f"🔔 Активних підписок на черги: <code>{subs_count}</code>"
    )
    await message.answer(text)
    
# Хендлер для команди /news
async def broadcast_news(message: types.Message):
    # 1. Перевірка на адміна
    if message.from_user.id != config.ADMIN_ID:
        return

    # 2. Визначаємо, що ми відправляємо (Копію чи Текст)
    is_copy_mode = False
    text_to_send = ""
    from_chat_id = None
    message_id_to_copy = None

    if message.reply_to_message:
        # ВАРІАНТ А: Ви відповіли на повідомлення (Для Преміум емодзі!)
        is_copy_mode = True
        from_chat_id = message.chat.id
        message_id_to_copy = message.reply_to_message.message_id
    else:
        # ВАРІАНТ Б: Ви просто написали текст після команди
        text_to_send = message.get_args()
        if not text_to_send:
            await message.answer(
                "ℹ️ <b>Як зробити розсилку:</b>\n\n"
                "1️⃣ <b>З Преміум емодзі/фото:</b> Напишіть пост у цей чат, натисніть на нього 'Відповісти' (Reply) і напишіть <code>/news</code>.\n"
                "2️⃣ <b>Тільки текст:</b> Напишіть <code>/news Ваш текст</code>",
                parse_mode="HTML"
            )
            return

    # 3. Отримуємо всіх користувачів
    with get_db() as conn:
        users = conn.execute("SELECT DISTINCT user_id FROM user_prefs").fetchall()

    if not users:
        await message.answer("🤷‍♂️ Немає користувачів для розсилки.")
        return

    count = 0
    error_count = 0
    
    status_msg = await message.answer(f"⏳ Починаю розсилку на {len(users)} користувачів...")

    # 4. Запускаємо цикл розсилки
    for user in users:
        user_id = user['user_id']
        try:
            if is_copy_mode:
                # ВИПРАВЛЕННЯ ТУТ: використовуємо message.bot замість просто bot
                await message.bot.copy_message(
                    chat_id=user_id, 
                    from_chat_id=from_chat_id, 
                    message_id=message_id_to_copy
                )
            else:
                # ВИПРАВЛЕННЯ ТУТ: використовуємо message.bot замість просто bot
                await message.bot.send_message(user_id, text_to_send, parse_mode="HTML")
            
            count += 1
            await asyncio.sleep(0.05) # Анти-спам затримка

        except Exception as e:
            print(f"Помилка розсилки для {user_id}: {e}")
            error_count += 1

    # 5. Звіт
    await status_msg.edit_text(
        f"✅ <b>Розсилка завершена!</b>\n\n"
        f"📧 Отримали: <code>{count}</code>\n"
        f"🚫 Не вдалося (заблокували бота): <code>{error_count}</code>",
        parse_mode="HTML"
    )

# Не забудь додати реєстрацію в функцію register_handlers:
# dp.register_message_handler(broadcast_news, commands=['news'])
# --- Notify Users Function ---
async def notify_users_about_update(bot, company, date_str, results):
    updated_queues = sorted({r['queue'] for r in results})
    queues_map = {}
    for r in results:
        queues_map.setdefault(r['queue'], []).append(r)

    with get_db() as conn:
        for queue in updated_queues:
            items = queues_map.get(queue, [])
            
            # Перевіряємо, чи є маркер порожнечі ('-' з парсера або 'empty' з бази)
            is_no_outages = any(it.get('off_time') in ['-', 'empty'] for it in items)

            total_off_minutes = 0
            schedule_data = [] # Зберігаємо дані як словники, щоб локалізувати потім

            if not is_no_outages:
                try:
                    items_sorted = sorted(items, key=lambda x: x.get('off_time', ''))
                except Exception:
                    items_sorted = items

                for it in items_sorted:
                    off = it.get('off_time', '').strip()
                    on = it.get('on_time', '').strip()
                    
                    if off and on and off not in ['-', 'empty']:
                        # Рахуємо тривалість відключення
                        try:
                            from datetime import datetime
                            t1 = datetime.strptime(off, '%H:%M')
                            t2 = datetime.strptime(on, '%H:%M')
                            
                            if on == '00:00' or t2 <= t1:
                                diff_minutes = 1440 - (t1.hour * 60 + t1.minute)
                            else:
                                diff_minutes = (t2 - t1).seconds // 60
                            
                            total_off_minutes += diff_minutes
                            
                            hours_val = round(diff_minutes / 60, 1)
                            display_hours = int(hours_val) if hours_val.is_integer() else hours_val
                        except Exception:
                            display_hours = 0
                            
                        schedule_data.append({
                            'off': off,
                            'on': on,
                            'hours': display_hours
                        })

            # Підсумки за добу
            off_h = round(total_off_minutes / 60, 1)
            on_h = round(24 - off_h, 1)
            
            fmt_off = int(off_h) if off_h.is_integer() else off_h
            fmt_on = int(on_h) if on_h.is_integer() else on_h

            users = conn.execute('''
                SELECT u.user_id, p.language 
                FROM users u
                LEFT JOIN user_prefs p ON u.user_id = p.user_id
                WHERE u.company = ? AND u.queue = ?
            ''', (company, queue)).fetchall()

            for user in users:
                lang = user['language'] or 'uk'
                
                # Заголовок
                header = get_text(lang, 'update_notify', company=company, queue=queue, date=format_display_date(date_str))
                
                # Футер з посиланням
                link_text = get_text(lang, 'monitor_link') if hasattr(get_text, 'monitor_link') else 'Монітор світла'
                # На випадок якщо в словнику ще немає ключів, використовуємо fallback значення через try-except або get
                try:
                    h_unit = get_text(lang, 'hour_short_dot')
                    outages_title = get_text(lang, 'notify_outages_title')
                    stats_title = get_text(lang, 'notify_stats_title')
                    on_label = get_text(lang, 'notify_on_label')
                    off_label = get_text(lang, 'notify_off_label')
                    footer_link = get_text(lang, 'monitor_link')
                except Exception:
                    h_unit = "год." if lang == 'uk' else "ч."
                    outages_title = "✅ Відключення:"
                    stats_title = "📊 Статистика:"
                    on_label = "⚡️ Зі світлом:"
                    off_label = "⚡️ Без світла:"
                    footer_link = "Монітор світла"

                footer = f"{footer_link}"
                
                if is_no_outages:
                    status_msg = get_text(lang, 'no_outages') 
                    text = f"{header}\n\n<b>{status_msg}</b>\n\n{footer}"
                elif schedule_data:
                    # Збираємо рядки графіку для конкретної мови користувача
                    lines_text = []
                    for sl in schedule_data:
                        lines_text.append(f'<tg-emoji emoji-id="6019346268197759615">🔌</tg-emoji> {sl["off"]} - {sl["on"]} ({sl["hours"]} {h_unit})')
                    
                    schedule_block = "\n".join(lines_text)
                    
                    text = (
                        f"{header}\n\n"
                        f"{outages_title}\n{schedule_block}\n\n"
                        f"{stats_title}\n"
                        f"{on_label} {fmt_on} {h_unit}\n"
                        f"{off_label} {fmt_off} {h_unit}"
                        f"\n\n{footer}"
                    )
                else:
                    text = header + footer
                    
                try:
                    await bot.send_message(
                        user['user_id'], 
                        text, 
                        parse_mode="HTML", 
                        disable_web_page_preview=True
                    )
                except Exception:
                    pass

# --- Handlers ---
async def cmd_tech_on(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    with get_db() as conn:
        conn.execute("UPDATE bot_settings SET value='1' WHERE key='tech_mode'")
        conn.commit()
    await message.answer("🚧 TECH MODE: ON")

async def cmd_tech_off(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    with get_db() as conn:
        conn.execute("UPDATE bot_settings SET value='0' WHERE key='tech_mode'")
        conn.commit()
    await message.answer("✅ TECH MODE: OFF")

async def upload_schedule(message: types.Message, scheduler):
    if message.from_user.id != ADMIN_ID: return
    raw_text = message.text.replace('/upload', '').strip()
    
    company, date_str, data = parse_schedule_text(raw_text)
    
    if not company or not date_str:
        return await message.answer("❌ Формат: ДТЕК 29.01.2026 ...")
    
    old_queues = {}
    with get_db() as conn:
        old_rows = conn.execute(
            "SELECT queue, off_time, on_time FROM schedules WHERE company = ? AND date = ?",
            (company, date_str)
        ).fetchall()
        for row in old_rows:
            q = row['queue']
            if q not in old_queues:
                old_queues[q] = []
            old_queues[q].append((row['off_time'], row['on_time']))

    for q in old_queues:
        old_queues[q] = sorted(old_queues[q])

    new_queues = {}
    for item in data:
        q = item['queue']
        if q not in new_queues:
            new_queues[q] = []
        # Замінюємо мінус на empty для порівняння
        off_cmp = 'empty' if item['off_time'] == '-' else item['off_time']
        on_cmp = 'empty' if item['on_time'] == '-' else item['on_time']
        new_queues[q].append((off_cmp, on_cmp))
        
    for q in new_queues:
        new_queues[q] = sorted(new_queues[q])

    changed_queues = set()
    for q, new_intervals in new_queues.items():
        old_intervals = old_queues.get(q, [])
        if new_intervals != old_intervals:
            changed_queues.add(q)
            
    if not changed_queues and old_queues:
        return await message.answer(f"✅ Графік {company} на {format_display_date(date_str)} <b>не змінився</b>. Розсилку скасовано.", parse_mode="HTML")

    with get_db() as conn:
        conn.execute("DELETE FROM schedules WHERE company = ? AND date = ?", (company, date_str))
        for item in data:
            # ЗДЕСЬ МАГІЯ: Якщо прочерк, пишемо 'empty'
            off_val = 'empty' if item['off_time'] == '-' else item['off_time']
            on_val = 'empty' if item['on_time'] == '-' else item['on_time']
            
            conn.execute(
                "INSERT INTO schedules (company, queue, date, off_time, on_time) VALUES (?,?,?,?,?)",
                (item['company'], item['queue'], item['date'], off_val, on_val)
            )
        conn.commit()

    await rebuild_jobs(message.bot, scheduler)
    
    changed_data = [item for item in data if item['queue'] in changed_queues]
    
    if changed_data:
        await notify_users_about_update(message.bot, company, date_str, changed_data)

    queues_map = {}
    for r in data:
        queues_map.setdefault(r['queue'], []).append(r)

    full_text_blocks = []
    for q, items in queues_map.items():
        is_no_outages = any(it.get('off_time') in ['-', 'empty'] for it in items)
        status_icon = "🔔" if q in changed_queues else "🔕 (без змін)"
        
        if is_no_outages:
            full_text_blocks.append(f"{company} {q} {status_icon}:\n✅ Відключень немає")
        else:
            try:
                items_sorted = sorted(items, key=lambda x: x.get('off_time', ''))
            except Exception:
                items_sorted = items
            lines = [f"""<tg-emoji emoji-id="5330017696660599813">🔴</tg-emoji> {it.get('off_time','').strip()} - <tg-emoji emoji-id="5330396907913098490">🟢</tg-emoji> {it.get('on_time','').strip()}""" for it in items_sorted if it.get('off_time') and it.get('on_time') and it.get('off_time') not in ['-', 'empty']]
            block = f"{company} {q} {status_icon}:\n" + "\n".join(lines) if lines else f"{company} {q} {status_icon}: (порожній графік)"
            full_text_blocks.append(block)

    full_schedules_text = "\n\n".join(full_text_blocks)
    await message.answer(f"✅ {company} ({format_display_date(date_str)}) завантажено!\nРозіслано сповіщень для {len(changed_queues)} черг.\n\n{full_schedules_text}")

def register_handlers(dp: Dispatcher, scheduler):
    dp.register_message_handler(cmd_tech_on, commands=['techon'])
    dp.register_message_handler(cmd_tech_off, commands=['techoff'])
    dp.register_message_handler(lambda m: upload_schedule(m, scheduler), commands=['upload'])
    dp.register_message_handler(admin_stats, commands=['stats'])
    dp.register_message_handler(broadcast_news, commands=['news'])
    dp.register_message_handler(download_db, commands=['getdb'])
    dp.register_message_handler(upload_db_via_bot, content_types=['document'])




























