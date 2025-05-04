from sqlalchemy import select, func
from database.db import get_db
from database.models import User, UserMovie


class UserRepository:
    @staticmethod
    async def get_user_by_discord_id(discord_id):
        db = await get_db()
        async with db.transaction():
            query = select(User).where(User.discord_id == discord_id)
            return await db.fetch_val(query)

    @staticmethod
    async def get_user_by_kinorium_id(kinorium_id):
        db = await get_db()
        async with db.transaction():
            query = select(User).where(User.kinorium_id == kinorium_id)
            return await db.fetch_val(query)

    @staticmethod
    async def get_kinorium_id_by_discord_id(discord_id):
        db = await get_db()
        async with db.transaction():
            query = select(User.kinorium_id).where(User.discord_id == discord_id)
            return await db.fetch_val(query)

    @staticmethod
    async def get_all_users():
        db = await get_db()
        async with db.transaction():
            query = select(User)
            return await db.fetch_all(query)

    @staticmethod
    async def get_movie_count_by_status(user_id, status):
        db = await get_db()
        async with db.transaction():
            query = (
                select(func.count())
                .select_from(UserMovie)
                .where(UserMovie.user_id == user_id, UserMovie.status == status)
            )
            return await db.fetch_val(query)
