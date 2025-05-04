import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
from bot import events as bot_events
from bot import commands as bot_commands
from database.db import init_db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

init_db()

bot_events.register_events(bot)
bot_commands.register_commands(bot)

bot.run(f"{TOKEN}")
