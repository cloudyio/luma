import discord
from discord.ext import commands

class functions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def change_bot_nick(self, guild, nick):
        bot_member = guild.get_member(self.bot.user.id)
        if bot_member:
            await bot_member.edit(nick=nick)
        
async def setup(bot):  
    await bot.add_cog(functions(bot)) 