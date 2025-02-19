import asyncio
import logging
import re
from playwright.async_api import async_playwright
from database.models import Movie
from database.db import get_db, init_db, connect_db, disconnect_db
from sqlalchemy import select, insert

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

PER_PAGE = 200
FIRST_PAGE = "https://ua.kinorium.com/user/112144/watchlist/?order=runtime&page=1&perpage={PER_PAGE}&mode=movie&nav_type=movie"
BASE_URL = "https://ua.kinorium.com/user/112144/watchlist/?order=runtime&&perpage={PER_PAGE}&mode=movie&nav_type=movie"

async def get_total_pages():
    """ Отримує кількість сторінок з першої сторінки """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(FIRST_PAGE.format(PER_PAGE=PER_PAGE))

        pages = await page.query_selector_all("#pagesSelect > ul > li > a")
        total_pages = len(pages)

        await browser.close()
        return total_pages

async def load_page(page, url):
    await page.goto(url, wait_until="networkidle")
    await page.evaluate("""
        () => {
            return new Promise((resolve) => {
                const scrollStep = 100;
                const delay = 100;
                
                const smoothScroll = () => {
                    const currentPos = window.scrollY;
                    window.scrollTo(0, currentPos + scrollStep);
                    
                    if (window.scrollY + window.innerHeight >= document.body.scrollHeight) {
                        resolve();
                    } else {
                        setTimeout(smoothScroll, delay);
                    }
                };
                
                smoothScroll();
            });
        }
    """)

async def parse_movie_data(page):
    movie_elements = await page.query_selector_all(".item.user-status-list.status_future")
    movies_data = []
    for element in movie_elements:
        # Отримуємо дані фільму
        title = await element.query_selector(".movie-title__text")
        title_text = await title.inner_text() if title else None

        # Отримуємо оригінальну назву та рік
        orig_name_elem = await element.query_selector(".item__name-orig")
        orig_name_text = await orig_name_elem.inner_text() if orig_name_elem else None

        # Отримуємо рік
        year_elem_text = orig_name_text.split(',')[-1].strip() if orig_name_text else None

        # Отримуємо жанр та тривалість
        extra_info_elem = await element.query_selector(".filmList__extra-info")
        extra_info_text = await extra_info_elem.inner_text() if extra_info_elem else None

        # Витягуємо runtime з extra_info
        runtime = None
        genre_text = None
        if extra_info_text:
            # Шукаємо формат "X год Y хв" або "Y хв"
            match = re.search(r'(?:(\d+)\s*год\s*)?(\d+)\s*хв', extra_info_text)
            if match:
                hours = int(match.group(1)) if match.group(1) else 0
                minutes = int(match.group(2))
                runtime = hours * 60 + minutes

            # Розділяємо genre_text і відкидаємо останню частину
            parts = extra_info_text.split(',')
            if len(parts) > 1:
                genre_text = ', '.join(parts[:-1]).strip()

        # Отримуємо режисера
        director_elem = await element.query_selector(".filmList__extra-info-director a")
        director_text = await director_elem.inner_text() if director_elem else None

        # Отримуємо рейтинг Кіноріум
        kinorium_rating_elem = await element.query_selector(".rating_kinorium .rating__value")
        kinorium_rating = await kinorium_rating_elem.inner_text() if kinorium_rating_elem else None

        # Отримуємо рейтинг IMDb
        imdb_rating_elem = await element.query_selector(".rating_imdb .value")
        imdb_rating = await imdb_rating_elem.inner_text() if imdb_rating_elem else None

        # Отримуємо посилання на зображення
        image_elem = await element.query_selector(".poster img")
        image_url = await image_elem.get_attribute("src") if image_elem else None

        # Додаємо кожен фільм у список
        movies_data.append({
            "title": title_text,
            "original_name": orig_name_text,
            "release_year": int(year_elem_text) if year_elem_text else None,
            "genre": genre_text,
            "runtime": runtime,
            "director": director_text,
            "kinorium_rating": float(kinorium_rating) if kinorium_rating and kinorium_rating.replace('.', '', 1).isdigit() else None,
            "imdb_rating": float(imdb_rating) if imdb_rating and imdb_rating.replace('.', '', 1).isdigit() else None,
            "image_url": image_url
        })
    return movies_data

async def save_movies_to_db(movies_data):
    async for db in get_db():
        query = insert(Movie)
        await db.execute_many(query=query, values=movies_data)
        logging.info(f"Додано {len(movies_data)} фільмів")

async def get_movie_details(page_num):
    logging.info(f"Початок обробки сторінки {page_num}")
    url = f"{BASE_URL.format(PER_PAGE=PER_PAGE)}&page={page_num}"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await load_page(page, url)
            movies_data = await parse_movie_data(page)
            await save_movies_to_db(movies_data)
            await browser.close()
            logging.info(f"Завершено обробку сторінки {page_num}")
    except Exception as e:
        logging.error(f"Помилка при обробці сторінки {page_num}: {e}")

async def scrape_all():
    """ Отримує всі сторінки та парсить їх асинхронно """
    # Ініціалізуємо базу даних (синхронно)
    init_db()

    # Підключаємося до бази даних (асинхронно)
    await connect_db()

    total_pages = await get_total_pages()
    logging.info(f"Знайдено сторінок: {total_pages}")

    tasks = [get_movie_details(i) for i in range(1, total_pages + 1)]
    await asyncio.gather(*tasks)

    # Відключаємося від бази даних (асинхронно)
    await disconnect_db()
    
    logging.info("Завершено парсинг та збереження фільмів у базу даних")

async def show_all_movies():
    """ Показує всі фільми з бази даних """
    async for db in get_db():
        async with db.transaction():
            result = await db.execute(select(Movie))
            logging.info("result: ", result)
            movies = await result.scalars()  # Отримуємо всі рядки як список
            for movie in movies:
                print(f"Назва: {movie.title}, Оригінальна назва: {movie.original_name}, Жанр: {movie.genre}, "
                      f"Тривалість: {movie.runtime} хв, Режисер: {movie.director}, "
                      f"Рейтинг Кіноріум: {movie.kinorium_rating}, Рейтинг IMDb: {movie.imdb_rating}, "
                      f"Зображення: {movie.image_url}")

if __name__ == "__main__":
    asyncio.run(scrape_all())
    # asyncio.run(show_all_movies())