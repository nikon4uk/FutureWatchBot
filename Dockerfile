FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy

USER root
RUN apt-get update && apt-get install -y cron && apt-get clean

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Playwright needs browsers installed
RUN playwright install chromium

# Копіюємо cron-розклад і ентрипоїнт
COPY cron/entrypoint.sh /entrypoint.sh
COPY cron/crontab /etc/cron.d/futurewatch-cron

RUN chmod +x /entrypoint.sh
RUN chmod 0644 /etc/cron.d/futurewatch-cron
RUN touch /var/log/cron.log

