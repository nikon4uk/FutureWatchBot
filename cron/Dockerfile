FROM python:3.12-slim

RUN apt-get update && apt-get install -y cron

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY cron/crontab /etc/cron.d/futurewatch-cron
COPY cron/entrypoint.sh /entrypoint.sh
RUN chmod 0644 /etc/cron.d/futurewatch-cron

RUN touch /var/log/cron.log

ENTRYPOINT ["/entrypoint.sh"]
