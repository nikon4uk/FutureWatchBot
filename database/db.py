from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from databases import Database

DATABASE_URL = "sqlite+aiosqlite:///./movies.db"

database = Database(DATABASE_URL)
metadata = MetaData()

Base = declarative_base(metadata=metadata)

# Ініціалізація бази даних
def init_db():
    # Створення таблиць
    engine = create_engine("sqlite:///./movies.db", echo=True, future=True)  # Використовуємо синхронний драйвер
    Base.metadata.create_all(bind=engine)

# Асинхронне підключення до бази даних
async def connect_db():
    await database.connect()

# Асинхронне відключення від бази даних
async def disconnect_db():
    await database.disconnect()

# Отримання сесії бази даних
async def get_db():
    async with database.transaction():
        yield database
