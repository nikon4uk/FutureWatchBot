def register_events(bot):
    @bot.event
    async def on_ready():
        await bot.wait_until_ready()
        try:
            synced = await bot.tree.sync()
            print(f"✅ Synchronized {len(synced)} slash command")
            print(f"Bot {bot.user.name} is ready to work!")
        except Exception as e:
            print(f"❌ Synchronization of teams: {e}")
