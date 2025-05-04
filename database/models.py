from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Enum,
    ForeignKey,
    Date,
    DateTime,
    select,
    insert,
    Index,
    func,
)
from sqlalchemy.orm import relationship
from database.db import Base
from enum import Enum as PyEnum


class UserMovieStatus(PyEnum):
    WATCHED = "watched"
    WATCH_LATER = "watch_later"


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    original_name = Column(String)
    release_year = Column(Integer)
    genre = Column(String)
    runtime = Column(Integer)
    director = Column(String)
    kinorium_title_link = Column(String)
    kinorium_rating = Column(Float)
    imdb_rating = Column(Float)
    image_url = Column(String)

    # Relationship with UserMovie
    user_movies = relationship("UserMovie", back_populates="movie")

    __table_args__ = (
        Index("ix_movie_title_year", "title", "release_year", unique=True),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(String, unique=True, nullable=False)
    kinorium_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)

    # Relationship with UserMovie
    movies = relationship("UserMovie", back_populates="user")


class UserMovie(Base):
    __tablename__ = "user_movies"
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    movie_id = Column(
        Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True
    )
    status = Column(Enum(UserMovieStatus))
    user_rating = Column(Integer, nullable=True)
    watched_date = Column(Date, nullable=True)
    added_date = Column(Date)

    user = relationship("User", back_populates="movies")
    movie = relationship("Movie", back_populates="user_movies")


class InsertedMovies(Base):
    __tablename__ = "temp_inserted_movies"

    id = Column(Integer, primary_key=True, autoincrement=True)


class MovieSearchSite(Base):
    __tablename__ = "movie_search_sites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    query_template = Column(String, nullable=False)

    def __repr__(self):
        return (
            f"<MovieSearchSite(name={self.name}, query_template={self.query_template})>"
        )


class MovieWheel(Base):
    __tablename__ = "movie_wheel"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)  # Should be only one wheel
    created_at = Column(DateTime, server_default=func.now())

    entries = relationship(
        "MovieWheelEntry", back_populates="wheel", cascade="all, delete-orphan"
    )


class MovieWheelEntry(Base):
    __tablename__ = "movie_wheel_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wheel_id = Column(Integer, ForeignKey("movie_wheel.id", ondelete="CASCADE"))
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"))
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE")
    )  # Who added the movie

    wheel = relationship("MovieWheel", back_populates="entries")
    movie = relationship("Movie")
    user = relationship("User")
