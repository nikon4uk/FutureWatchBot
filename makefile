# Збірка образу
build:
	docker compose build

# Запуск усіх сервісів
up:
	docker compose up -d

# Перезапуск сервісів
restart:
	docker compose down && docker compose up -d

# Зупинка контейнерів
down:
	docker compose down

# Логи бота
logs-bot:
	docker compose logs -f bot

# Логи скрапера (cron)
logs-scraper:
	docker compose logs -f scraper

# Дебаг скрапера вручну
scraper-shell:
	docker compose run --rm scraper bash

# Ручний запуск скрапера
run-scraper:
	docker compose run --rm scraper python -m scraper.scraper

# Очистка контейнерів і образів (уважно!)
clean:
	docker compose down --volumes --remove-orphans
	docker system prune -f

