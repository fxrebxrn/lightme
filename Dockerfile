# Используем стабильный образ Python 3.10
FROM python:3.10-slim

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Отключаем создание файлов кэша .pyc и включаем немедленный вывод логов в консоль
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Копируем только файл зависимостей сначала (для кэширования слоев Docker)
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все остальные файлы проекта в контейнер
COPY . .

# ЗАМЕНИ main.py НА НАЗВАНИЕ СВОЕГО ГЛАВНОГО ФАЙЛА (например, bot.py)
CMD ["python", "main.py"]
