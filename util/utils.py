from util.mongo import Mongo
from discord.ext import commands
import discord
from datetime import datetime
import re
import os
from datetime import timedelta
import dotenv

dotenv.load_dotenv()
bot = Mongo('bot')

dev_emojis = {
    "ban": "<:ban:1316117188058419281>",
    "unban": "<:unban:1316118745080660072>",
    "kick": "<:kick:1316120626720931890>",
    "alert": "<:alert:1316120013727334430>",
    "timeout": "<:timeout:1316121356647137330>",
    "untimeout": "<:untimeout:1316121317451497563>",
    "warn": "<:warn:1316130616751951872>",
    "pardon": "<:pardon:1316132939855171614>",
}

permissions_key = {
    'ban': "ban_members",
    'unban': "ban_members",
    'kick': "kick_members",
    'timeout': "moderate_members",
    'untimeout': "moderate_members",
    'warn': "kick_members",
    'pardon': "kick_members",
    'manage': "manage_guild"
}

async def time_format(ctx, time):
    pattern = re.compile(r'((?P<weeks>\d+)w)?((?P<days>\d+)d)?((?P<hours>\d+)h)?((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?')
    match = pattern.fullmatch(time)
    if not match:
        await ctx.send('Invalid time format, please use the following format: 1w2d3h4m5s')
        return None
    
    time_params = {name: int(value) for name, value in match.groupdict(default=0).items()}
    return timedelta(**time_params)

def has_permission(permission_type):
    async def predicate(ctx):
        permissions = await bot.find_one('permissions', {'_id': ctx.guild.id})
        if not permissions or not permissions.get(permission_type):
            if hasattr(ctx.author.guild_permissions, permissions_key[permission_type]):
                return True
            return False
        
        allowed_roles = permissions[permission_type]['allowed_roles']
        for role in ctx.author.roles:
            if role.id in allowed_roles:
                return True
            
        allowed_users = permissions[permission_type]['allowed_users']
        if ctx.author.id in allowed_users:
            return True
        
        allowed_permissions = permissions[permission_type]['allowed_permissions']
        for permission in allowed_permissions:
            if getattr(ctx.author.guild_permissions, permission):
                return True
        
        overwrites = permissions['overwrites']
        if ctx.author.id in overwrites:
                return True
        return False
    return commands.check(predicate)


async def log_action(ctx, action, user, guild, reason='None provided'):
    if action in ['ban', 'unban', 'kick', 'timeout', 'untimeout', 'warn', 'pardon']:
        data = {
        'action': action,
        'user': user.id,
        'guild': guild.id,
        'reason': reason,
        'timestamp': datetime.now()
        }
        await bot.insert_one('moderation', data)

    config = await bot.find_one('config', {'_id': guild.id})
    if not config or not config.get('log_channel') or not config['log_channel'].get(action):
        return
    
    channel = guild.get_channel(config['log_channel'][action])
    if not channel:
        await ctx.send('Your log channel is not set up correctly')
        return
    
    embed = discord.Embed(
        title=f'{action.capitalize()}',
        description=f'User: {user.mention}\nReason: {reason}',
        color=0x00ff00,
    )
    
    await channel.send(embed=embed)
    
    return data

class Emojis:
    def __init__(self):
        if os.getenv("ENVIRONMENT") == "prod":
            emojis = os.getenv("prod_emojis")
        elif os.getenv("ENVIRONMENT") == "dev":
            emojis = dev_emojis
        else:
            emojis = None
            raise ValueError("Invalid environment")
        
        if emojis:
            if isinstance(emojis, str):
                emojis_dict = eval(emojis)
            else:
                emojis_dict = emojis
            for name, value in emojis_dict.items():
                setattr(self, name, value)

emojis = Emojis()


