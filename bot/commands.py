import asyncio
from discord.ui import View, Button, Select
from discord import Embed, ButtonStyle, SelectOption, Interaction, InteractionResponse
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from services.movie_service import MovieService
from services.movie_wheel_service import MovieWheelService
from services.user_service import UserService
from database.models import User
from database.db import get_db, connect_db, disconnect_db
from parser.scraper import (
    get_total_pages,
    fetch_movies_from_page,
    get_total_movies,
    save_movies_to_db,
)
from urllib.parse import quote
from bot.gif_generation import delete_gif
from bot.gif_generation import (
    send_gif,
    anitmation_runtime,
    create_gif_and_get_winner_movie,
)
import logging
from discord.ext import commands


movie_service = MovieService()
user_service = UserService()
wheel_service = MovieWheelService()


async def link_user_to_kinorium(discord_id, kinorium_id, user_name):
    db = await get_db()
    # Logic for saving connection in database
    try:
        query = insert(User).values(
            discord_id=discord_id, kinorium_id=kinorium_id, username=user_name
        )
        await db.execute(query)
    except IntegrityError as e:
        logging.error(f"User with this ID already exists in database: {e}")
    except Exception as e:
        logging.error(f"Error saving connection to database: {e}")


async def scrape_page_and_update_progress(
    page_number: int,
    kinorium_id: int,
    progress_queue: asyncio.Queue,
    is_rated: bool = False,
) -> list:
    """Gets movie data from a specific page and updates progress."""
    movies_data = await fetch_movies_from_page(
        page_number, kinorium_id, is_rated=is_rated
    )
    await progress_queue.put(len(movies_data))  # Update progress
    return movies_data


async def scrape_user_movies(kinorium_id: int, ctx):
    """Gets all pages and parses them asynchronously for a specific user."""
    await connect_db()
    try:
        # Get total pages and movies count for each list
        total_pages_watch_list = await get_total_pages(kinorium_id, is_rated=False)
        total_movies_watch_list = await get_total_movies(kinorium_id, is_rated=False)
        total_pages_rated_list = await get_total_pages(kinorium_id, is_rated=True)
        total_movies_rated_list = await get_total_movies(kinorium_id, is_rated=True)

        # Total movies count
        total_movies = total_movies_watch_list + total_movies_rated_list

        # Start parsing message
        progress_message = await ctx.send(
            f"Parsing movies... 0 of {total_movies} completed."
        )

        # Queue for progress updates
        progress_queue = asyncio.Queue()

        # Tasks for page parsing
        tasks = []

        # Parse pages for "Watch Later" list
        for page in range(1, total_pages_watch_list + 1):
            tasks.append(
                scrape_page_and_update_progress(
                    page, kinorium_id, progress_queue, is_rated=False
                )
            )

        # Parse pages for "Rated Movies" list
        for page in range(1, total_pages_rated_list + 1):
            tasks.append(
                scrape_page_and_update_progress(
                    page, kinorium_id, progress_queue, is_rated=True
                )
            )

        # Start progress updates
        asyncio.create_task(
            update_progress(progress_queue, total_movies, progress_message)
        )

        # Collect all movies
        all_movies_data = await asyncio.gather(*tasks)
        all_movies_data = [movie for sublist in all_movies_data for movie in sublist]

        logging.info(f"Found movies: {len(all_movies_data)}")

        # Save movies to database
        user_id = await user_service.get_user_by_kinorium_id(kinorium_id)
        await save_movies_to_db(all_movies_data, user_id)

        await progress_message.edit(
            content=f"Movie parsing completed! Total movies: {total_movies}."
        )
    except Exception as e:
        logging.error(f"Error parsing movies: {e}")
        await ctx.send("Error parsing movies.")
    finally:
        await disconnect_db()


async def update_progress(
    progress_queue: asyncio.Queue, total_movies: int, progress_message
):
    """Updates progress update message."""
    completed_movies = 0
    while completed_movies < total_movies:
        movies_processed = await progress_queue.get()  # Get data from queue
        completed_movies += movies_processed  # Increment completed movies counter
        await progress_message.edit(
            content=f"Parsing movies... {completed_movies} of {total_movies} completed."
        )


async def get_random_movie(ctx, number: int = 1):
    discord_user_id = ctx.author.id
    user_id = await user_service.get_user_by_discord_id(discord_user_id)
    return await movie_service.get_random_movie_recommendations(user_id, number)


def create_movie_embed(movie):
    embed = Embed(
        title=movie.title,
        description=movie.genre,
        url=movie.kinorium_title_link,
        color=0x00FF00,
    )
    embed.set_image(url=movie.image_url)
    embed.add_field(name="Duration", value=f"{movie.runtime} min", inline=True)
    embed.add_field(name="Release Year", value=movie.release_year, inline=True)
    embed.add_field(name="Director", value=movie.director, inline=True)
    embed.set_footer(
        text=f"IMDb Rating: {movie.imdb_rating} | Kinorium: {movie.kinorium_rating}"
    )
    return embed


def create_winmovie_embed(movie):
    embed = Embed(
        title=movie.title,
        description=movie.genre,
        url=movie.kinorium_title_link,
        color=0xFFFF00,
    )

    url_parts = movie.image_url.split("/")
    url_parts.pop(4)
    url_parts.insert(4, "300")
    big_image_url = "/".join(url_parts)

    embed.set_image(url=big_image_url)
    embed.add_field(name="Duration", value=f"{movie.runtime} min", inline=True)
    embed.add_field(name="Release Year", value=movie.release_year, inline=True)
    embed.add_field(name="Director", value=movie.director, inline=True)
    embed.set_footer(
        text=f"IMDb Rating: {movie.imdb_rating} | Kinorium: {movie.kinorium_rating}"
    )
    return embed


class BaseMovieView(View):
    GOOGLE_SEARCH_TEMPLATE = (
        "http://www.google.com/search?q={query}+українською+uakino.club"
    )

    def __init__(self, user_id, movie, sites):
        super().__init__()
        self.user_id = user_id
        self.sites = sites
        self.movie = movie
        self.add_search_buttons()

    def create_site_button(self, site) -> Button:
        return Button(
            label=site.name,
            url=f"{site.query_template}{quote(self.movie.title)}",
            style=ButtonStyle.link,
        )

    def create_google_button(self) -> Button:
        return Button(
            label="Google 🔍",
            url=self.GOOGLE_SEARCH_TEMPLATE.format(query=quote(self.movie.title)),
            style=ButtonStyle.link,
        )

    def add_search_buttons(self):
        for site in self.sites:
            self.add_item(self.create_site_button(site))
        self.add_item(self.create_google_button())


class MovieView(BaseMovieView):
    def __init__(self, user_id, movie, sites, wheel_movies):
        super().__init__(user_id, movie, sites)
        self.wheel_movies = wheel_movies
        self.add_wheel_buttons()

    def add_wheel_buttons(self):
        # Add a button to control the wheel
        movies_title = (
            [movie.title for movie in self.wheel_movies] if self.wheel_movies else []
        )

        if self.movie.title in movies_title:
            self.add_item(RemoveFromWheelButton(self.user_id, self.movie, self.sites))
        else:
            self.add_item(AddToWheelButton(self.user_id, self.movie, self.sites))


class WinMovieView(BaseMovieView):
    def __init__(self, user_id, movie, sites):
        super().__init__(user_id, movie, sites)


# Add "Add to the Wheel"
class AddToWheelButton(Button):
    def __init__(self, user_id, movie, sites):
        super().__init__(label="➕ Add to wheel", style=ButtonStyle.green)
        self.user_id = user_id
        self.movie = movie
        self.sites = sites

    async def callback(self, interaction):
        await wheel_service.add_movie_to_wheel(
            user_id=self.user_id, movie_id=self.movie.id
        )
        wheel_movies = await wheel_service.get_movies_in_wheel()

        await interaction.response.edit_message(
            view=MovieView(
                self.user_id,
                movie=self.movie,
                sites=self.sites,
                wheel_movies=wheel_movies,
            )
        )
        await interaction.followup.send(
            f"✅ **{self.movie.title}** added to the wheel!\n"
            f"👉 Use `!wheel` or `/wheel` to view."
        )


# Remove from the Wheel
class RemoveFromWheelButton(Button):
    def __init__(self, user_id, movie, sites):
        super().__init__(label="❌ Remove from the wheel", style=ButtonStyle.red)
        self.user_id = user_id
        self.movie = movie
        self.sites = sites

    async def callback(self, interaction):
        await wheel_service.delete_movie_from_wheel(movie_id=self.movie.id)

        await interaction.response.edit_message(
            view=MovieView(
                self.user_id, movie=self.movie, sites=self.sites, wheel_movies=[]
            )
        )
        await interaction.followup.send(f"❌ **{self.movie.title}** removed from the wheel!")


class MovieToDeleteSelect(Select):
    def __init__(self, movies):
        # Check for duplicates
        seen_movies = set()
        unique_movies = []
        for movie in movies:
            if movie.id not in seen_movies:
                seen_movies.add(movie.id)
                unique_movies.append(movie)
            else:
                logging.warning(
                    f"Found duplicate movie: {movie.title} (ID: {movie.id})"
                )

        # Create options only for unique movies
        options = []
        for i, movie in enumerate(unique_movies):
            option = SelectOption(
                label=f"{movie.title} ({movie.release_year})",
                value=f"movie_{i}_{movie.id}",  # Add index for uniqueness
                description=f"Director: {movie.director}",
            )
            options.append(option)
            logging.info(f"Added option: {option.label} with value: {option.value}")

        super().__init__(
            placeholder="Select movie to remove",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: Interaction):
        # Get movie ID from value
        movie_id = int(self.values[0].split("_")[-1])
        await wheel_service.delete_movie_from_wheel(movie_id=movie_id)

        # Update movie list
        updated_movies = await wheel_service.get_movies_in_wheel()

        if updated_movies:
            embed = Embed(
                title="🎡 Wheel of Movies",
                description="\n".join(
                    f"🎬 {m.title} ({m.release_year})" for m in updated_movies
                ),
                color=0xFFD700,
            )
        else:
            embed = Embed(
                title="🎡 Wheel of Movies",
                description="🔍 Your movie wheel is empty.",
                color=0xFFD700,
            )

        view = WheelView(self.view.bot, updated_movies)
        await interaction.response.edit_message(embed=embed, view=view)


class MovieSearchSelect(Select):
    def __init__(self, movies, search_query: str):
        # Create base options
        if movies:
            options = [
                SelectOption(
                    label=f"{m.title} ({m.release_year})",
                    value=str(m.id),
                    description=f"Director: {m.director}" if m.director else None,
                )
                for m in movies[:25]  # Limit to 25 options (Discord limit)
            ]
        else:
            options = [SelectOption(label="No movies found", value="0")]

        super().__init__(
            placeholder=f"Found {len(movies)} movies",
            options=options,
            disabled=not movies,  # Disable only if movies is empty
        )

    async def callback(self, interaction: Interaction):
        if self.values[0] == "0":
            return

        movie_id = int(self.values[0])

        try:
            # Add movie to wheel
            user_id = await user_service.get_user_by_discord_id(interaction.user.id)

            await wheel_service.add_movie_to_wheel(movie_id=movie_id, user_id=user_id)

            # Get updated movie list in wheel
            updated_movies = await wheel_service.get_movies_in_wheel()

            # Create new embed for wheel
            if updated_movies:
                embed = Embed(
                    title="🎡 Wheel of Movies",
                    description="\n".join(
                        f"🎬 {m.title} ({m.release_year})" for m in updated_movies
                    ),
                    color=0xFFD700,
                )
            else:
                embed = Embed(
                    title="🎡 Wheel of Movies",
                    description="🔍 Your movie wheel is empty.",
                    color=0xFFD700,
                )

            # Create new view for wheel
            view = WheelView(self.view.bot, updated_movies)

            # Update message
            await interaction.response.edit_message(
                content=None,  # Remove old content
                embed=embed,
                view=view,
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error adding movie: {str(e)}", ephemeral=True
            )


class SearchMoviesView(View):
    def __init__(self, bot, search_query: str):
        super().__init__()
        self.bot = bot
        self.search_query = search_query

    async def setup(self):
        found_movies = await movie_service.search_movies(self.search_query)

        # Add Select with search results
        self.add_item(MovieSearchSelect(found_movies, self.search_query))


class WheelView(View):
    def __init__(self, bot, movies):
        super().__init__()
        self.bot = bot
        self.movies = movies

        # Add Select for removing movies
        if movies:
            self.add_item(MovieToDeleteSelect(movies))

        # Clear button
        clear_button = Button(label="Clear all wheel", style=ButtonStyle.danger)
        clear_button.callback = self.clear_wheel
        self.add_item(clear_button)

        # Spin button
        spin_button = Button(label="Spin", style=ButtonStyle.primary)
        spin_button.callback = self.spin_wheel
        self.add_item(spin_button)

    async def clear_wheel(self, interaction: Interaction):
        # Clear all wheel
        await wheel_service.clear_wheel()
        await interaction.response.send_message("Wheel has been cleared.", ephemeral=True)

    async def spin_wheel(self, interaction: Interaction):
        # Send response to avoid errors
        await interaction.message.delete()
        await interaction.response.defer()

        # Get context for spin command
        ctx = await self.bot.get_context(interaction.message)

        # Change context to match spin command
        ctx.command = self.bot.get_command("spin")  # Get spin command object
        ctx.invoked_with = "spin"  # Specify that command was called as "spin"

        # Call command via invoke
        await self.bot.invoke(ctx)


def create_help_embed() -> Embed:
    """Creates embed with command help"""
    embed = Embed(
        title="📖 Command Help",
        description="List of all available bot commands",
        color=0x3498DB,
    )

    commands_info = {
        "🎬 Main Commands": {
            "!register [kinorium_id]": "Link your Discord to Kinorium",
            "!random or !r": "Get a random movie from your Watch Later list",
            "!search [title] or !m [title]": "Search for a movie by title",
        },
        "🎡 Wheel Commands": {
            "!wheel or !w": "Show all movies in the wheel",
            "!spin or !s": "Spin the wheel and select a random movie",
        },
        "⚙️ Admin Commands": {
            "!addsite [name] [url]": "Add new movie search site",
            "!clear": "Clear chat",
        },
    }

    for category, commands in commands_info.items():
        commands_text = "\n".join(f"`{cmd}` - {desc}" for cmd, desc in commands.items())
        embed.add_field(name=category, value=commands_text, inline=False)

    return embed


def register_commands(bot):
    @bot.command()
    @commands.has_permissions(administrator=True)
    async def addsite(ctx, name: str, query_template: str):
        """Adds new movie search site. Available only to administrators."""
        try:
            await movie_service.add_search_site(name, query_template)
            await ctx.send(f"Site '{name}' successfully added!")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @addsite.error
    async def add_site_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "You don't have administrator permissions to run this command."
            )

    def extract_kinorium_id(input_str: str) -> int:
        """Extracts Kinorium ID from URL or returns the ID if it's a number"""
        try:
            # If it's a number, just convert to int
            if input_str.isdigit():
                return int(input_str)

            # If it's a URL, extract ID
            if "kinorium.com/user/" in input_str:
                # Remove trailing slash if present
                input_str = input_str.rstrip("/")
                # Take last part of URL after /user/
                user_id = input_str.split("/user/")[-1]
                return int(user_id)

            raise ValueError("Invalid ID format")
        except (ValueError, IndexError) as e:
            raise ValueError("Invalid ID or link format")

    @bot.command()
    async def register(ctx, kinorium_input: str):
        """
        Registers user by their Kinorium ID or profile link
        Examples:
        !register 112144
        !register https://ua.kinorium.com/user/112144/
        """
        discord_user_id = ctx.author.id
        user_name = ctx.author.name

        try:
            kinorium_id = extract_kinorium_id(kinorium_input)

            await link_user_to_kinorium(discord_user_id, kinorium_id, user_name)
            await ctx.send(
                f"Hi, {user_name}! I've started collecting your movies from Kinorium."
            )
            await scrape_user_movies(kinorium_id, ctx)
            await ctx.send(
                "You've been successfully registered! Your Discord is linked to Kinorium"
            )

        except ValueError as e:
            await ctx.send(
                f"❌ Error: {e} Invalid ID or link format\n"
                "Examples of correct format:\n"
                "`!register 112144`\n"
                "`!register https://ua.kinorium.com/user/112144/`"
            )
        except Exception as e:
            logging.error(f"Registration error: {e}")
            await ctx.send("❌ Registration error")

    @bot.command(aliases=["r"])
    async def random(ctx):
        try:
            movie = await get_random_movie(ctx)
            movie = movie[0]
            if movie:
                embed = create_movie_embed(movie)
                sites = (
                    await movie_service.get_all_search_sites()
                )  # Get sites here
                wheel_movies = await wheel_service.get_movies_in_wheel()
                user_id = await user_service.get_user_by_discord_id(ctx.author.id)

                view = MovieView(
                    user_id, movie, sites, wheel_movies
                )  # Pass sites to MovieView
                await ctx.send(
                    embed=embed, view=view
                )  # Send Embed with View
            else:
                await ctx.send(
                    "You haven't added any movies to your Watch Later list yet."
                )
        except Exception as e:
            logging.error(f"Error getting random movie: {e}")
            await ctx.send("Error getting random movie.")

    @bot.command(aliases=["m"])
    async def search(ctx, *, query: str):
        view = SearchMoviesView(bot, query)
        await view.setup()

        await ctx.send(content=f"🔍 Search results for '{query}'", view=view)

    @bot.command(aliases=["s"])
    async def spin(ctx):
        try:
            loading_message = await ctx.send("🎡 Spinning wheel...")
            # Send "Spinning wheel..." message

            movies = await wheel_service.get_movies_in_wheel()
            if not movies:
                await loading_message.delete()
                await ctx.send("🎡 Wheel is empty! Add movies to start the game.")
                return None

            gif_path = f"case_opening_{len(movies)}_films.gif"

            winner_movie = await create_gif_and_get_winner_movie(ctx, movies, gif_path)

            await loading_message.delete()

            measage_with_gif = await send_gif(ctx, gif_path)

            winner_user = await wheel_service.get_winner_user(winner_movie.id)

            await wheel_service.delete_movie_from_wheel(winner_movie.id)

            embed = create_winmovie_embed(winner_movie)

            sites = await movie_service.get_all_search_sites()  # Get sites here

            user_id = await user_service.get_user_by_discord_id(ctx.author.id)

            view = WinMovieView(
                user_id, winner_movie, sites
            )  # Pass sites to MovieView

            gif_runtime = await anitmation_runtime()

            await asyncio.sleep(gif_runtime)

            await measage_with_gif.delete()

            await ctx.send(
                f"🎉 Spin for {winner_user.username} 🎉 \n Winning movie:",
                embed=embed,
                view=view,
            )

            await delete_gif(gif_path)

        except Exception as e:
            logging.error(f"Error sending GIF {e}")

    async def show_wheel_logic(target):
        """Common logic for !wheel and /wheel"""
        wheel_movies = await wheel_service.get_movies_in_wheel()
        if wheel_movies:
            embed = Embed(
                title="🎡 Wheel of Movies",
                description="\n".join(
                    f"🎬 {m.title} ({m.release_year})" for m in wheel_movies
                ),
                color=0xFFFF00,
            )
            view = WheelView(bot, wheel_movies)

            if isinstance(target, InteractionResponse):
                await target.send_message(embed=embed, view=view)
            else:
                await target.send(embed=embed, view=view)
        else:
            if isinstance(target, InteractionResponse):
                await target.send_message("🔍 Your movie wheel is empty.")
            else:
                await target.send("🔍 Your movie wheel is empty.")

    # Slash command /wheel
    @bot.tree.command(name="wheel", description="Show all movies in the wheel")
    async def show_wheel_slash(interaction: Interaction):
        await show_wheel_logic(interaction.response)

    # Text command !wheel or !w
    @bot.command(aliases=["wheel", "w"])
    async def show_wheel(ctx):
        await show_wheel_logic(ctx)

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def clear(ctx):
        def is_not_pinned(message):
            return not message.pinned

        await ctx.channel.purge(check=is_not_pinned)

    # Slash command /info
    @bot.tree.command(
        name="info", description="Get help for all available commands"
    )
    async def info_slash(interaction: Interaction):
        await interaction.response.send_message(embed=create_help_embed())

    # Text command !info or !i
    @bot.command(aliases=["i"])
    async def info(ctx):
        await ctx.send(embed=create_help_embed())
