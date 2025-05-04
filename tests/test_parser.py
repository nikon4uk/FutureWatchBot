import re

# Приклади тексту
examples = [
    "документальний, сімейний, 1 год 31 хв",
    "документальний, 2 години",
    "сімейний, 45 хв",
    "1 год 20 хв",
    "30 хв",  # Тестуємо випадок, коли вказані тільки хвилини
    "1 година 15 хв",  # Тестуємо випадок, коли вказані години та хвилини
    "2 години 5 хв"  # Тестуємо випадок, коли вказані години та хвилини
]

for extra_info_text in examples:
    match = re.search(r'.*?(\d+)\s*год(?:ина|ини)?(?:\s*(\d+)\s*хв)?|(?:\s*(\d+)\s*хв)', extra_info_text)

    if match:
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else (int(match.group(3)) if match.group(3) else 0)
        runtime = hours * 60 + minutes
        print(f"Тривалість '{extra_info_text}': {runtime} хвилин")
    else:
        print(f"Тривалість не знайдена для '{extra_info_text}'.")