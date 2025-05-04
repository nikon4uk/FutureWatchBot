from typing import Optional
import logging
from database.repositories.movie_wheel_repository import WheelRepository


class MovieWheelService:
    """Service class for managing movie wheel operations"""
    _instance: Optional["MovieWheelService"] = None
    repository: WheelRepository

    def __new__(cls) -> "MovieWheelService":
        """Singleton pattern implementation for MovieWheelService"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.repository = WheelRepository()
        return cls._instance

    async def get_or_create_global_wheel(self):
        """
        Retrieve the global wheel or create a new one if it doesn't exist
        
        Returns:
            int: The ID of the global wheel
        """
        try:
            wheel_id = await self.repository.get_global_wheel()
            if wheel_id is None:
                wheel_id = await self.repository.create_global_wheel()
                logging.info("A new global wheel was created")
                return wheel_id
            return wheel_id

        except Exception as e:
            logging.error(f"Error when receiving/creating a wheel: {e}")
            raise

    async def add_movie_to_wheel(self, movie_id: int, user_id: int):
        """
        Add a movie to the wheel
        
        Args:
            movie_id (int): ID of the movie to add
            user_id (int): ID of the user adding the movie
        """
        try:
            wheel_id = await self.get_or_create_global_wheel()
            await self.repository.add_movie_to_wheel(movie_id, user_id, wheel_id)
            logging.info(f"The movie {movie_id} was added to the wheel by user {user_id}")

        except Exception as e:
            logging.error(f"Error when adding a movie to the wheel: {e}")
            raise

    async def delete_movie_from_wheel(self, movie_id: int):
        """
        Remove a movie from the wheel
        
        Args:
            movie_id (int): ID of the movie to remove
        """
        try:
            wheel_id = await self.get_or_create_global_wheel()
            await self.repository.delete_movie_from_wheel(movie_id, wheel_id)
            logging.info(f"The movie {movie_id} is removed from the wheel")

        except Exception as e:
            logging.error(f"Error when the movie is removed from the wheel: {e}")
            raise

    async def clear_wheel(self):
        """Clear all movies from the wheel"""
        try:
            wheel_id = await self.get_or_create_global_wheel()
            await self.repository.clear_wheel(wheel_id)
            logging.info("The wheel is cleaned")

        except Exception as e:
            logging.error(f"Error when cleaning the wheel: {e}")
            raise

    async def get_movies_in_wheel(self):
        """
        Get a list of all movies currently in the wheel
        
        Returns:
            list: List of movies in the wheel
        """
        try:
            wheel_id = await self.get_or_create_global_wheel()
            movies = await self.repository.get_movies_in_wheel(wheel_id)
            logging.info(f"Obtained {len(movies)} movies from the wheel")
            return movies

        except Exception as e:
            logging.error(f"Error when receiving movies from a wheel: {e}")
            return []

    async def get_winner_user(self, movie_id: int):
        """
        Get the user who added the winning movie
        
        Args:
            movie_id (int): ID of the winning movie
            
        Returns:
            User: User who added the movie, or None if not found
        """
        try:
            wheel_id = await self.get_or_create_global_wheel()
            user = await self.repository.get_winner_user(movie_id, wheel_id)
            if user:
                logging.info(f"The winner found for the movie {movie_id}")
            else:
                logging.info(f"The winner for the movie {movie_id} was not found")
            return user

        except Exception as e:
            logging.error(f"Error when receiving the winner: {e}")
            return None
