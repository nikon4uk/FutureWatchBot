from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from databases import Database
import logging

DATABASE_URL = "sqlite+aiosqlite:///./movies.db"

database = Database(DATABASE_URL)
metadata = MetaData()

Base = declarative_base(metadata=metadata)


# Database initialization
def init_db():
    # Create tables
    engine = create_engine(
        "sqlite:///./movies.db", echo=True, future=True
    )  # Using synchronous driver
    Base.metadata.create_all(bind=engine)

    # Create trigger
    create_trigger(engine)


def create_trigger(engine):
    """Trigger to record inserted movies in the temporary table temp_inserted_movies"""
    with engine.connect() as connection:
        connection.execute(
            text(
                """
                CREATE TRIGGER IF NOT EXISTS after_inserted_movie
                AFTER INSERT
                ON movies
                FOR EACH ROW
                BEGIN
                    INSERT INTO temp_inserted_movies (id)
                    VALUES (NEW.id);
                END;
                """
            )
        )


# Asynchronous database connection
async def connect_db():
    await database.connect()
    await database.execute("PRAGMA journal_mode=WAL;")


# Asynchronous database disconnection
async def disconnect_db():
    await database.disconnect()


# Get database session
async def get_db():
    async with database.transaction() as transaction:
        try:
            return database
        except Exception as e:
            logging.error(f"Database usage error: {e}")
            await transaction.rollback()  # Try to rollback transaction
