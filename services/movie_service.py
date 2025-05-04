from typing import Optional
import logging
from database.repositories.movie_repository import MovieRepository


class MovieService:
    """Service class for managing movie operations"""
    _instance: Optional["MovieService"] = None
    repository: MovieRepository

    def __new__(cls):
        """Singleton pattern implementation for MovieService"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.repository = MovieRepository()
        return cls._instance

    async def search_movies(self, search_query: str):
        """
        Search for movies by title
        
        Args:
            search_query (str): The search query to find movies
            
        Returns:
            list: List of movies matching the search query
        """
        try:
            movies = await self.repository.search_by_title(search_query)
            if not movies:
                logging.info(f"No movies found for query '{search_query}'")
            else:
                logging.info(
                    f"Found {len(movies)} movies for query '{search_query}'"
                )
            return movies
        except Exception as e:
            logging.error(
                f"Error searching movies for query '{search_query}': {e}"
            )
            return []

    async def get_random_movie_recommendations(self, user_id: int, count: int = 1):
        """
        Get random movie recommendations for a user
        
        Args:
            user_id (int): ID of the user
            count (int): Number of recommendations to return
            
        Returns:
            list: List of random movie recommendations
        """
        try:
            movies = await self.repository.get_random_movies(user_id, count)
            if not movies:
                logging.info(f"No movies found for user {user_id}")
            else:
                logging.info(
                    f"Found {len(movies)} random movies for user {user_id}"
                )
            return movies
        except Exception as e:
            logging.error(
                f"Error getting random movies for user {user_id}: {e}"
            )
            return []

    async def add_search_site(self, name: str, query_template: str):
        """
        Add a new search site
        
        Args:
            name (str): Name of the search site
            query_template (str): Template for search queries
        """
        try:
            await self.repository.add_search_site(name, query_template)
            logging.info(f"Search site {name} added successfully")
        except Exception as e:
            logging.error(f"Error adding search site {name}: {e}")
            raise

    async def get_all_search_sites(self):
        """
        Get all available search sites
        
        Returns:
            list: List of all search sites
        """
        try:
            sites = await self.repository.get_all_search_sites()
            logging.info(f"Retrieved {len(sites)} search sites")
            return sites
        except Exception as e:
            logging.error(f"Error getting search sites: {e}")
            return []