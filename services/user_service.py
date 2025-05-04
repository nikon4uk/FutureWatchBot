from typing import Optional
from database.repositories.user_repository import UserRepository
import logging


class UserService:
    """Service class for managing user operations"""
    _instance: Optional["UserService"] = None
    repository: UserRepository

    def __new__(cls):
        """Singleton pattern implementation for UserService"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.repository = UserRepository()
        return cls._instance

    async def get_user_by_discord_id(self, discord_id):
        """
        Get a user by their Discord ID
        
        Args:
            discord_id: The Discord ID of the user
            
        Returns:
            User: User object if found, None otherwise
        """
        try:
            user = await self.repository.get_user_by_discord_id(discord_id)
            if user is None:
                logging.warning(f"User with discord_id {discord_id} not found.")
            return user

        except Exception as e:
            logging.error(
                f"Error getting user with discord_id {discord_id}: {e}"
            )
            return None

    async def get_user_by_kinorium_id(self, kinorium_id):
        """
        Get a user by their Kinorium ID
        
        Args:
            kinorium_id: The Kinorium ID of the user
            
        Returns:
            User: User object if found, None otherwise
        """
        try:
            user = await self.repository.get_user_by_kinorium_id(kinorium_id)
            if user is None:
                logging.warning(f"User with kinorium_id {kinorium_id} not found.")
            return user

        except Exception as e:
            logging.error(
                f"Error getting user with kinorium_id {kinorium_id}: {e}"
            )
            return None

    async def get_kinorium_id_by_discord_id(self, discord_id):
        """
        Get a user's Kinorium ID by their Discord ID
        
        Args:
            discord_id: The Discord ID of the user
            
        Returns:
            str: Kinorium ID if found, None otherwise
        """
        try:
            user = await self.repository.get_kinorium_id_by_discord_id(discord_id)
            if user is None:
                logging.warning(f"User with discord_id {discord_id} not found.")
            return user

        except Exception as e:
            logging.error(
                f"Error getting user with discord_id {discord_id}: {e}"
            )
            return None

    async def get_all_users(self):
        """
        Get all users in the system
        
        Returns:
            list: List of all users
        """
        try:
            users = await self.repository.get_all_users()
            if users is None:
                logging.warning("No users found")
            return users

        except Exception as e:
            logging.error(f"Error getting users: {e}")
            return []

    async def get_movie_count_by_status(self, user_id, status):
        """
        Get the count of movies with a specific status for a user
        
        Args:
            user_id: ID of the user
            status: Status to count movies for
            
        Returns:
            int: Count of movies with the specified status
        """
        try:
            total = await self.repository.get_movie_count_by_status(user_id, status)
            if total is None:
                logging.warning(f"List {status} is empty for user {user_id}")
            return total

        except Exception as e:
            logging.error(
                f"Error getting movie count with status {status} for user {user_id}: {e}"
            )
            return None