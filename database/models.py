from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from database.db import Base

class Movie(Base):
    __tablename__ = 'movies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    original_name = Column(String)
    release_year = Column(Integer)
    genre = Column(String)
    runtime = Column(Integer)
    director = Column(String)
    kinorium_rating = Column(Float)
    imdb_rating = Column(Float)
    image_url = Column(String)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(String, unique=True, nullable=False)
    username = Column(String)

class WatchLater(Base):
    __tablename__ = 'watch_later'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    movie_id = Column(Integer, ForeignKey('movies.id'), primary_key=True)
    added_date = Column(Date)

    user = relationship("User", back_populates="watch_later")
    movie = relationship("Movie", back_populates="watch_later")

User.watch_later = relationship("WatchLater", back_populates="user")
Movie.watch_later = relationship("WatchLater", back_populates="movie")
