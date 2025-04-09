FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .
COPY wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh

# Создание директории для логов
RUN mkdir -p /app/logs

# Установка переменных окружения по умолчанию
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Запуск приложения
CMD ["python", "main.py"]