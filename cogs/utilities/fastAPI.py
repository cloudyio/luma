import discord
from discord.ext import commands
from server import init_server

class FastAPI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_server(self.check_guilds_in_bot)

    async def check_guilds_in_bot(self, guild_ids):
        guilds_in_bot = []
        for guild_id in guild_ids:
            guild = self.bot.get_guild(guild_id)
            if guild:
                guilds_in_bot.append({"id": guild.id, "name": guild.name})
        return guilds_in_bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.bot.user} is ready for FastAPI requests.")

async def setup(bot):
    await bot.add_cog(FastAPI(bot))