from util.mongo import Mongo
from discord.ext import commands
import discord
from datetime import datetime as dt
import datetime
import re
import os
import random
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
    "right": "<:right:1317497147045970013>",
    "left": "<:left:1317497124619030601>"
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

def generate_string(length=5):
    characters = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    return ''.join(random.choice(characters) for _ in range(length))

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
        config = await bot.find_one('config', {'_id': str(ctx.guild.id)})
        print(ctx.guild.id)
        if not config:
            await ctx.send(f'{emojis.alert} **this guild has not been setup!**')
            return False

        permissions = config['permissions']
        
        try:
            if getattr(ctx.author.guild_permissions, permissions_key[permission_type]):
                return True
        except:
            pass

        if permission_type in permissions:
            allowed_roles = permissions[permission_type].get('allowed_roles', [])
            for role in ctx.author.roles:
                if role.id in allowed_roles:
                    return True
                
            allowed_users = permissions[permission_type].get('allowed_users', [])
            if str(ctx.author.id) in allowed_users:
                return True
            
            allowed_permissions = permissions[permission_type].get('allowed_permissions', [])
            for permission in allowed_permissions:
                if getattr(ctx.author.guild_permissions, permission):
                    return True

        overwrites = permissions.get('overwrites', [])
        if ctx.author.id in overwrites:
            return True
        
        await ctx.send(f'{emojis.alert} You do not have permission to use this command')
        return False
    return commands.check(predicate)

async def log_action(ctx, action, user, guild, reason='None provided'):
    if action in ['ban', 'unban', 'kick', 'timeout', 'untimeout', 'warn', 'pardon']:
        
        while True:
            log_id = generate_string()
            print(log_id)
            if not await bot.find_one('moderation', {'_id': log_id}):
                break

        data = { 
        '_id': log_id,
        'action': action,
        'user': user.id,
        'guild': guild.id,
        'reason': reason,
        'timestamp': dt.now(datetime.timezone.utc)
        }
        await bot.insert_one('moderation', data)

    config = await bot.find_one('config', {'_id': guild.id})
    
    if not config or not config.get('log_channels') or not config['log_channels'].get(action):
        return
    
    channel = guild.get_channel(config['log_channels'][action])
    if not channel:
        pass
    
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

class Pagnination(discord.ui.View):
    def __init__(self, pages):
        super().__init__()
        self.pages = pages
        self.current_page = 0
        self.message = None

    async def update_page(self, interaction):
        self.current.label = f'{self.current_page + 1}/{len(self.pages)}'
        embed = self.pages[self.current_page]
        await interaction.response.edit_message(embed=embed, view=self)


    @discord.ui.button(label='', emoji = emojis.left, style=discord.ButtonStyle.primary)
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(0, self.current_page - 1)
        await self.update_page(interaction)

    @discord.ui.button(label='0/0' ,style=discord.ButtonStyle.gray, disabled=True)
    async def current(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label='', emoji=emojis.right ,style=discord.ButtonStyle.primary)
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        await self.update_page(interaction)

        


