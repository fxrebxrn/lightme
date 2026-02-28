import re
from datetime import datetime

def parse_schedule_text(text):
    lines = text.split('\n')
    if not lines: return None, None, []

    header = lines[0].strip().upper()
    # Regex: Шукаємо КОМПАНІЮ та ДАТУ (dd.mm.yyyy)
    match = re.search(r'^(ЦЕК|ДТЕК|DTEK)\s+(\d{2}\.\d{2}\.\d{4})', header)
    
    if not match:
        return None, None, []

    company = "ЦЕК" if "ЦЕК" in match.group(1) else "ДТЕК"
    date_str = match.group(2) 
    
    try:
        date_obj = datetime.strptime(date_str, '%d.%m.%Y')
        db_date = date_obj.strftime('%Y-%m-%d')
    except ValueError:
        return None, None, []

    current_queue = ""
    results = []

    for line in lines[1:]:
        line = line.strip()
        if not line: continue

        # Визначаємо чергу
        queue_match = re.search(r'(?:Черга|Група)\s*(\d+(?:\.\d+)?)', line, re.IGNORECASE)
        if queue_match:
            current_queue = queue_match.group(1)
            continue
            
        # --- ВИПРАВЛЕННЯ: Ігноруємо "немає відключень" ---
        # Якщо в рядку написано "немає", "нет", "0" або "-", 
        # ми просто не додаємо цей запис у результати.
        # Тоді планувальник не буде намагатися парсити прочерки.
        clean_line = line.lower().replace(" ", "")
        if clean_line in ['-', 'немає', 'нет', '0', 'нема', 'відключеньнемає']:
            # Додаємо спеціальну "затичку", щоб база знала, що ми оновили дані, 
            # але відключень реально 0. Ми використаємо слово 'empty'.
            results.append({
                'company': company,
                'queue': current_queue,
                'date': db_date,
                'off_time': 'empty', 
                'on_time': 'empty'
            })
            continue

        # Парсимо час (напр. 10:00 - 14:00)
        time_match = re.findall(r'(\d{1,2}:\d{2})\s*[-—–]\s*(\d{1,2}:\d{2})', line)
        if time_match and current_queue:
            for start, end in time_match:
                results.append({
                    'company': company,
                    'queue': current_queue,
                    'date': db_date,
                    'off_time': start.zfill(5),
                    'on_time': end.zfill(5)
                })

    return company, db_date, results
