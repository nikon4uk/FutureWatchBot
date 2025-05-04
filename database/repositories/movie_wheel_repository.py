from sqlalchemy import select, insert, delete
from database.db import get_db
from database.models import Movie, MovieWheel, MovieWheelEntry, User


class WheelRepository:
    @staticmethod
    async def get_global_wheel():
        """Get a global wheel"""
        db = await get_db()
        async with db.transaction():
            query = select(MovieWheel).where(MovieWheel.name == "Global Wheel")
            wheel = await db.fetch_one(query)
            return wheel.id if wheel else None

    @staticmethod
    async def create_global_wheel():
        """Create a global wheel"""
        db = await get_db()
        async with db.transaction():
            query = (
                insert(MovieWheel).values(name="Global Wheel").returning(MovieWheel.id)
            )
            return await db.fetch_val(query)

    @classmethod
    async def add_movie_to_wheel(
        cls, movie_id: int, user_id: int, wheel_id: int = None
    ):
        """Add a movie to the wheel"""
        db = await get_db()
        async with db.transaction():
            wheel_id = await cls.get_global_wheel() if wheel_id is None else wheel_id

            query = insert(MovieWheelEntry).values(
                wheel_id=wheel_id, movie_id=movie_id, user_id=user_id
            )
            await db.execute(query)

    @classmethod
    async def delete_movie_from_wheel(cls, movie_id: int, wheel_id: int = None):
        """Remove the movie from the wheel"""
        db = await get_db()
        async with db.transaction():
            wheel_id = await cls.get_global_wheel() if wheel_id is None else wheel_id

            query = delete(MovieWheelEntry).where(
                MovieWheelEntry.wheel_id == wheel_id,
                MovieWheelEntry.movie_id == movie_id,
            )
            await db.execute(query)

    @classmethod
    async def clear_wheel(cls, wheel_id: int = None):
        """Clean the wheel"""
        db = await get_db()
        async with db.transaction():
            wheel_id = await cls.get_global_wheel() if wheel_id is None else wheel_id

            query = delete(MovieWheelEntry).where(MovieWheelEntry.wheel_id == wheel_id)
            await db.execute(query)

    @classmethod
    async def get_movies_in_wheel(cls, wheel_id: int = None):
        """Get a list of movies in the wheel"""
        db = await get_db()
        wheel_id = await cls.get_global_wheel() if wheel_id is None else wheel_id
        async with db.transaction():
            query = (
                select(Movie)
                .join(MovieWheelEntry)
                .where(MovieWheelEntry.wheel_id == wheel_id)
            )
            return await db.fetch_all(query)

    @classmethod
    async def get_winner_user(cls, movie_id: int, wheel_id: int = None):
        """We get a winning movie user"""
        db = await get_db()
        wheel_id = await cls.get_global_wheel() if wheel_id is None else wheel_id
        async with db.transaction():
            query = (
                select(User)
                .join(MovieWheelEntry)
                .where(
                    MovieWheelEntry.wheel_id == wheel_id,
                    MovieWheelEntry.movie_id == movie_id,
                )
            )
            return await db.fetch_one(query)
