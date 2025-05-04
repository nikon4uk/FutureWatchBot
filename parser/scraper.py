import asyncio
import logging
import re
from playwright.async_api import async_playwright
from database.models import Movie, UserMovie, User, InsertedMovies, UserMovieStatus
from database.db import get_db
from sqlalchemy import select, and_, or_
from sqlalchemy.dialects.sqlite import insert
from asyncio import Semaphore

# Logging configuration

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(lineno)d - %(message)s"
)
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

semaphore = Semaphore(1)

PER_PAGE = 100
PAGE_NUMBER_ONE = 1

FIRST_PAGE_WATCHLIST = "https://ua.kinorium.com/user/{kinorium_id}/watchlist/?order=date&page=1&perpage={PER_PAGE}&mode=movie&nav_type=movie%2Canimation&company_type=production"
WATCHLIST_URL = "https://ua.kinorium.com/user/{kinorium_id}/watchlist/?order=date&&perpage={PER_PAGE}&mode=movie&nav_type=movie%2Canimation&company_type=production"

FIRST_PAGE_RATEDLIST = "https://ua.kinorium.com/user/{kinorium_id}/ratings/?mode=movie&nav_type=movie%2Canimation&company_type=production&perpage={PER_PAGE}&order=date&page=1"
RATEDLIST_URL = "https://ua.kinorium.com/user/{kinorium_id}/ratings/?mode=movie&nav_type=movie%2Canimation&company_type=production&perpage={PER_PAGE}&order=date"


async def get_total_pages(kinorium_id, is_rated: bool = False):
    """Get the number of pages from the first page for a specific user"""
    url = FIRST_PAGE_RATEDLIST if is_rated else FIRST_PAGE_WATCHLIST
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url.format(kinorium_id=kinorium_id, PER_PAGE=PER_PAGE))

        last_page_elem = await page.query_selector(
            "#pagesSelect > ul > li:last-child > a"
        )
        total_pages = await last_page_elem.inner_text() if last_page_elem else 1
        result = int(total_pages)

        await browser.close()
        return result


async def get_total_movies(kinorium_id, is_rated: bool = False):
    """Get the number of movies for a specific user"""
    url = FIRST_PAGE_RATEDLIST if is_rated else FIRST_PAGE_WATCHLIST

    def get_last_number(text):
        # We divide the line by spaces

        parts = text.split()
        # We find the last element that is the number

        for part in reversed(parts):
            if part.isdigit():
                return int(part)
        return None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url.format(kinorium_id=kinorium_id, PER_PAGE=PER_PAGE))
        total_movies_elem = await page.query_selector("#pagesSelect > span")
        total_movies = get_last_number(await total_movies_elem.inner_text())
        await browser.close()
        return total_movies


async def load_page(page, url):
    """Load a page and perform smooth scrolling"""
    await page.goto(url, wait_until="networkidle")
    await page.evaluate(
        """
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
    """
    )


async def parse_movie_data(page, movie_selector: str):
    """Parse movie data from the page using the specified selector"""
    movie_elements = await page.query_selector_all(movie_selector)
    movies_data = []
    for element in movie_elements:
        # We get a movie data

        title = await element.query_selector(".movie-title__text")
        title_text = await title.inner_text() if title else None

        kinorium_title_link_elem = await element.query_selector(
            ".filmList__item-title-link"
        )
        kinorium_title_link = f"https://ua.kinorium.com{await kinorium_title_link_elem.get_attribute('href')}"

        # We get the original name and year

        orig_name_elem = await element.query_selector(".item__name-orig")
        orig_name_text = await orig_name_elem.inner_text() if orig_name_elem else None

        # We get a year

        year_elem_text = (
            orig_name_text.split(",")[-1].strip() if orig_name_text else None
        )

        # We get a genre and duration

        extra_info_elem = await element.query_selector(".filmList__extra-info")
        extra_info_text = (
            await extra_info_elem.inner_text() if extra_info_elem else None
        )

        # We pull out Runtime from Extra_info

        runtime = None
        genre_text = None
        if extra_info_text:
            # Looking for a "x h m min" format or "y min or x hours"

            match = re.search(
                r".*?(\d+)\s*год(?:ина|ини|ин)?(?:\s*(\d+)\s*хв)?|(?:\s*(\d+)\s*хв)",
                extra_info_text,
            )

            if match:
                hours = int(match.group(1)) if match.group(1) else 0
                minutes = (
                    int(match.group(2))
                    if match.group(2)
                    else (int(match.group(3)) if match.group(3) else 0)
                )
                runtime = hours * 60 + minutes
            # Divide genre_text and discard the last part

            parts = extra_info_text.split(",")
            if len(parts) > 1:
                genre_text = ", ".join(parts[:-1]).strip()

        # We get the director

        director_elem = await element.query_selector(".filmList__extra-info-director a")
        director_text = await director_elem.inner_text() if director_elem else None

        # We get a movie rating

        kinorium_rating_elem = await element.query_selector(
            ".rating_kinorium .rating__value"
        )
        kinorium_rating = (
            await kinorium_rating_elem.inner_text() if kinorium_rating_elem else None
        )

        # We get an IMDB rating

        imdb_rating_elem = await element.query_selector(".rating_imdb .value")
        imdb_rating = await imdb_rating_elem.inner_text() if imdb_rating_elem else None

        # We get a link to the image

        image_elem = await element.query_selector(".poster img")
        image_url = await image_elem.get_attribute("src") if image_elem else None

        # Receives a user rating

        user_rating_elem = await element.query_selector(
            "div.statusWidgetData.statusWidget.done span"
        )
        user_rating = None

        if user_rating_elem:
            class_name = await user_rating_elem.get_attribute("class")
            match = re.search(r"number-(\d+)", class_name)
            user_rating = int(match.group(1)) if match else 0

        # We add each movie to the list

        movies_data.append(
            {
                "title": title_text,
                "original_name": orig_name_text,
                "release_year": int(year_elem_text) if year_elem_text else None,
                "genre": genre_text,
                "runtime": runtime,
                "director": director_text,
                "kinorium_rating": (
                    float(kinorium_rating)
                    if kinorium_rating and kinorium_rating.replace(".", "", 1).isdigit()
                    else None
                ),
                "imdb_rating": (
                    float(imdb_rating)
                    if imdb_rating and imdb_rating.replace(".", "", 1).isdigit()
                    else None
                ),
                "image_url": image_url,
                "kinorium_title_link": kinorium_title_link,
                "user_rating": user_rating,
            }
        )
    return movies_data


async def parse_watch_list_movie_data(page):
    """Parse movie data from the watchlist page"""
    return await parse_movie_data(page, ".item.user-status-list.status_future")


async def parse_rated_movie_data(page):
    """Parse movie data from the rated movies page"""
    return await parse_movie_data(page, ".item.user-status-list.status_done")


async def save_movies_to_db(movies_data, user_id, batch_size=250):
    """Save movies to the database in batches"""
    async with semaphore:
        try:
            db = await get_db()
            # Split the list of movies into batches

            for i in range(0, len(movies_data), batch_size):
                batch = movies_data[i : i + batch_size]
                logging.info(
                    f"Processing batch {i//batch_size + 1} of {len(movies_data)//batch_size + 1} "
                    f"(movies {i+1}-{min(i+batch_size, len(movies_data))})"
                )

                async with db.transaction():
                    existing_movies = await get_existing_movies(db, batch)
                    new_movies = filter_new_movies(batch, existing_movies)
                    new_movies_ids = (
                        await insert_new_movies(db, new_movies) if new_movies else []
                    )

                    existing_user_movies = await get_existing_user_movies(db, user_id)
                    user_movie_values = build_user_movie_links(
                        batch,
                        existing_movies,
                        new_movies,
                        new_movies_ids,
                        existing_user_movies,
                        user_id,
                    )

                    if user_movie_values:
                        logging.info(
                            f"Established {len(user_movie_values)} links in batch {i//batch_size + 1}"
                        )
                        await save_user_movie_links(db, user_movie_values)

        except Exception as e:
            logging.error(f"Error saving movies to database: {e}")

    logging.info(f"Processed all {len(movies_data)} movies for user {user_id}")


async def get_existing_movies(db, movies_data):
    """Get a list of movies that already exist in the database"""
    titles_years = [(m["title"], m["release_year"]) for m in movies_data]
    query = select(Movie).where(
        or_(
            *[
                and_(Movie.title == title, Movie.release_year == year)
                for title, year in titles_years
            ]
        )
    )
    return await db.fetch_all(query)


def filter_new_movies(movies_data, existing_movies):
    """Filter out new movies that are not yet in the database"""
    existing_set = {(movie.title, movie.release_year) for movie in existing_movies}
    return [
        movie
        for movie in movies_data
        if (movie["title"], movie["release_year"]) not in existing_set
    ]


async def insert_new_movies(db, new_movies):
    """Add new movies to the database and return their IDs"""
    movies_to_insert = [
        {
            key: m[key]
            for key in [
                "title",
                "original_name",
                "release_year",
                "genre",
                "runtime",
                "director",
                "kinorium_rating",
                "imdb_rating",
                "image_url",
                "kinorium_title_link",
            ]
        }
        for m in new_movies
    ]

    await db.execute_many(insert(Movie), values=movies_to_insert)

    new_movies_ids_records = await db.fetch_all(select(InsertedMovies.id))
    await db.execute("DELETE FROM temp_inserted_movies;")

    return [record.id for record in new_movies_ids_records]


async def get_existing_user_movies(db, user_id):
    """Get existing user-movie relationships"""
    query = select(UserMovie).where(UserMovie.user_id == user_id)
    return await db.fetch_all(query)


def build_user_movie_links(
    movies_data,
    existing_movies,
    new_movies,
    new_movies_ids,
    existing_user_movies,
    user_id,
):
    """Create a list of user-movie relationships"""
    existing_user_movie_set = {(um.movie_id, um.status) for um in existing_user_movies}
    user_movie_values = []

    for movie in existing_movies:
        user_rating = next(
            (m["user_rating"] for m in movies_data if m["title"] == movie.title), None
        )
        status = (
            UserMovieStatus.WATCHED
            if user_rating is not None
            else UserMovieStatus.WATCH_LATER
        )
        if (movie.id, status) not in existing_user_movie_set:
            user_movie_values.append(
                {
                    "user_id": user_id,
                    "movie_id": movie.id,
                    "status": status,
                    "user_rating": user_rating,
                }
            )

    for movie_data, movie_id in zip(new_movies, new_movies_ids):
        user_rating = movie_data.get("user_rating")
        status = (
            UserMovieStatus.WATCHED
            if user_rating is not None
            else UserMovieStatus.WATCH_LATER
        )
        user_movie_values.append(
            {
                "user_id": user_id,
                "movie_id": movie_id,
                "status": status,
                "user_rating": user_rating,
            }
        )

    return user_movie_values


async def save_user_movie_links(db, user_movie_values):
    """Save user-movie relationships to the database"""
    insert_query = insert(UserMovie).values(user_movie_values)
    insert_query = insert_query.on_conflict_do_update(
        index_elements=["user_id", "movie_id"],
        set_={
            "status": insert_query.excluded.status,
            "user_rating": insert_query.excluded.user_rating,
        },
    )
    await db.execute(insert_query)


async def fetch_movies_from_page(
    page_num: int, kinorium_id: int, is_rated: bool = False
) -> list:
    """Fetch movie data from a specific page (watchlist or rated)"""
    logging.info(
        f"Starting to process page {page_num} for {'rated' if is_rated else 'watchlist'} movies"
    )

    url = (RATEDLIST_URL if is_rated else WATCHLIST_URL).format(
        PER_PAGE=PER_PAGE, kinorium_id=kinorium_id
    )
    url += f"&page={page_num}"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await load_page(page, url)

            # We use the appropriate Parsing function

            movies_data = await (
                parse_rated_movie_data(page)
                if is_rated
                else parse_watch_list_movie_data(page)
            )

            await browser.close()
            logging.info(
                f"Completed processing page {page_num} for {'rated' if is_rated else 'watchlist'} movies"
            )
            return movies_data
    except Exception as e:
        logging.error(f"Error processing page {page_num}: {e}")


async def scrape_user_movies(*user_data):
    """Scrape movies for a specific user"""
    user_id, kinorium_id = user_data

    # We run a few asynchronous tasks in parallel

    get_total_movies_rated_task = get_total_movies(kinorium_id, is_rated=True)
    get_total_movies_watchlist_task = get_total_movies(kinorium_id)
    total_watchlist_movies_on_db_task = UserMovie.get_movie_count_by_status(
        user_id, UserMovieStatus.WATCH_LATER
    )
    total_rated_movies_on_db_task = UserMovie.get_movie_count_by_status(
        user_id, UserMovieStatus.WATCHED
    )

    # Looking forward to all tasks

    total_rated_movies_on_site, total_watchlist_movies_on_site = await asyncio.gather(
        get_total_movies_rated_task, get_total_movies_watchlist_task
    )
    total_watchlist_movies_on_db, total_rated_movies_on_db = await asyncio.gather(
        total_watchlist_movies_on_db_task, total_rated_movies_on_db_task
    )

    if (
        total_rated_movies_on_site != total_rated_movies_on_db
        or total_watchlist_movies_on_site != total_watchlist_movies_on_db
    ):
        # Start parallel to the task to get movies

        movies_rated_task = fetch_movies_from_page(
            PAGE_NUMBER_ONE, kinorium_id, is_rated=True
        )
        movies_watchlist_task = fetch_movies_from_page(PAGE_NUMBER_ONE, kinorium_id)

        # Looking forward to completing both requests

        movies_rated, movies_watchlist = await asyncio.gather(
            movies_rated_task, movies_watchlist_task
        )

        # We combine movies and keep them in a database

        movies_all = movies_rated + movies_watchlist
        await save_movies_to_db(movies_all, user_id)
    else:
        logging.info(f"User {user_id} does not need to update lists")

    print(
        total_rated_movies_on_site,
        total_rated_movies_on_db,
        total_watchlist_movies_on_site,
        total_watchlist_movies_on_db,
    )


async def scrape_all_users():
    """Scrape movies for all users"""
    users = [(user.id, user.kinorium_id) for user in await User.get_all_users()]

    tasks = [scrape_user_movies(*user) for user in users]
    await asyncio.gather(*tasks)

    logging.info(
        "Completed scraping and saving movies to database for all users"
    )


if __name__ == "__main__":
    asyncio.run(scrape_all_users())
