from sqlalchemy import select, or_, func, insert
from database.db import get_db
from database.models import Movie, UserMovie, UserMovieStatus, MovieSearchSite


class MovieRepository:
    @staticmethod
    async def search_by_title(search_query: str):
        """
        Searches for movies by title (both original and translated).
        Returns a list of movies that contain the search term.
        """
        db = await get_db()
        async with db.transaction():
            search_query = search_query.strip()

            search_patterns = [
                f"%{search_query}%",  # Exact query
                f"%{search_query.lower()}%",  # Lowercase
                f"%{search_query.upper()}%",  # Uppercase
                f"%{search_query.capitalize()}%",  # First letter is capitalized
            ]

            conditions = or_(
                *[
                    or_(Movie.title.ilike(pattern), Movie.original_name.ilike(pattern))
                    for pattern in search_patterns
                ]
            )

            query = select(Movie).where(conditions).order_by(Movie.title)

            return await db.fetch_all(query)

    @staticmethod
    async def get_random_movies(user_id: int, number: int = 1):
        db = await get_db()
        async with db.transaction():
            query = (
                select(Movie)
                .join(UserMovie)
                .where(
                    UserMovie.user_id == user_id,
                    UserMovie.status == UserMovieStatus.WATCH_LATER,
                )
                .order_by(func.random())
                .limit(number)
            )
            return await db.fetch_all(query)

    @staticmethod
    async def add_search_site(name: str, query_template: str):
        db = await get_db()
        async with db.transaction():
            query = insert(MovieSearchSite).values(
                name=name, query_template=query_template
            )
            return await db.execute(query)

    @staticmethod
    async def get_all_search_sites():
        db = await get_db()
        async with db.transaction():
            query = select(MovieSearchSite)
            return await db.fetch_all(query)
