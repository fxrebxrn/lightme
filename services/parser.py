import re
from datetime import datetime

NO_OUTAGES_TOKENS = {
    '-', 'немає', 'нет', '0', 'нема', 'відключеньнемає', 'безвідключень', 'безотключений'
}


def parse_schedule_text(text: str):
    lines = (text or '').splitlines()
    if not lines:
        return None, None, []

    header = lines[0].strip().upper()
    match = re.search(r'^(ЦЕК|ДТЕК|DTEK)\s+(\d{2}\.\d{2}\.\d{4})', header)
    if not match:
        return None, None, []

    company = "ЦЕК" if "ЦЕК" in match.group(1) else "ДТЕК"
    date_str = match.group(2)

    try:
        db_date = datetime.strptime(date_str, '%d.%m.%Y').strftime('%Y-%m-%d')
    except ValueError:
        return None, None, []

    current_queue = ""
    results = []

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue

        queue_match = re.search(r'(?:Черга|Група)\s*(\d+(?:\.\d+)?)', line, re.IGNORECASE)
        if queue_match:
            current_queue = queue_match.group(1)
            continue

        clean_line = line.lower().replace(" ", "")
        if clean_line in NO_OUTAGES_TOKENS and current_queue:
            results.append(
                {
                    'company': company,
                    'queue': current_queue,
                    'date': db_date,
                    'off_time': 'empty',
                    'on_time': 'empty',
                }
            )
            continue

        # Поддержка нескольких интервалов в одной строке
        time_match = re.findall(r'(\d{1,2}:\d{2})\s*[-—–]\s*(\d{1,2}:\d{2})', line)
        if time_match and current_queue:
            for start, end in time_match:
                results.append(
                    {
                        'company': company,
                        'queue': current_queue,
                        'date': db_date,
                        'off_time': start.zfill(5),
                        'on_time': end.zfill(5),
                    }
                )

    return company, db_date, results