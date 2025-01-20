import discord
import os
import util.utils as utils
from discord.ext import commands
from util.mongo import Mongo

bot = Mongo('bot')
emojis = utils.emojis

class ModerationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def delete_messages(self, ctx, bot_message):
        await ctx.message.delete(delay=3)
        await bot_message.delete(delay=3)

    @commands.hybrid_command()
    @utils.has_permission('ban')
    async def ban(self, ctx, member: discord.Member,*, reason: str = "None provided"):
        print(f"Running ban command: {ctx.author} attempting to ban {member}")
        if member == ctx.author:
            await ctx.send(f'{emojis.alert} You cant ban yourself!')
            return
        elif member.top_role >= ctx.author.top_role:
            await ctx.send(f'{emojis.alert} You cannot ban someone with the same or a higher role than you')
            return
        try:
        
            # await member.ban(reason=reason)
            pass
        except discord.errors.Forbidden:
            await ctx.send(f'{emojis.alert} I do not have permission to ban this user')
            return
        
        bot_message = await ctx.send(f'{emojis.ban} **{member}** has been banned. Reason: **{reason}**')
        await utils.log_action(ctx, 'ban', member, ctx.guild, reason)
        await self.delete_messages(ctx, bot_message)
        

    @commands.hybrid_command()
    @utils.has_permission('unban')
    async def unban(self, ctx, user: discord.User,*, reason: str = "None provided"):
        try:
            await ctx.guild.unban(user, reason=reason)
        except discord.errors.NotFound:
            await ctx.send(f'{emojis.alert} **{user}** is not banned!')
            return
        except discord.errors.Forbidden:
            await ctx.send(f'{emojis.alert} I do not have permission to unban this user')
            return
        
        bot_message = await ctx.send(f'{emojis.unban} **{user}** has been unbanned!')
        await utils.log_action(ctx, 'unban', user, ctx.guild, reason)
        await self.delete_messages(ctx, bot_message)


    @commands.hybrid_command()
    @utils.has_permission('kick')
    async def kick(self, ctx, member: discord.Member,*, reason: str= "None provided"):
        if member == ctx.author:
            await ctx.send(f'{emojis.alert} You cant kick yourself!')
            return
        elif member.top_role >= ctx.author.top_role:
            await ctx.send(f'{emojis.alert} You cannot kick someone with the same or a higher role than you!')
            return
        
        try:
            await member.kick(reason=reason)
        except discord.errors.Forbidden:
            await ctx.send(f'{emojis.alert} I do not have permission to kick this user')
            return
        
        bot_message = await ctx.send(f'{emojis.kick} **{member}** has been kicked. Reason: **{reason}**')
        await utils.log_action(ctx, 'kick', member, ctx.guild, reason)
        await self.delete_messages(ctx, bot_message)


    @commands.hybrid_command()
    @utils.has_permission('timeout')
    async def timeout(self, ctx, member: discord.Member, length: str,*, reason: str = "None provided"):
        if member == ctx.author:
            await ctx.send(f'{emojis.alert} You cant timeout yourself!')
            return
        elif member.top_role >= ctx.author.top_role:
            await ctx.send(f'{emojis.alert} You cannot timeout someone with the same or a higher role than you!')
            return
        
        delta = await utils.time_format(ctx, length)
        if not delta:
            return
        
        try:
            await member.timeout(delta, reason=reason)
        except discord.errors.Forbidden:
            await ctx.send(f'{emojis.alert} I do not have permission to timeout this user')
            return
        
        bot_message = await ctx.send(f'{emojis.timeout} **{member}** has been timed out. Reason: **{reason}**')
        await utils.log_action(ctx, 'timeout', member, ctx.guild, reason)
        await self.delete_messages(ctx, bot_message)


    @commands.hybrid_command()
    @utils.has_permission('untimeout')
    async def untimeout(self, ctx, member: discord.Member,*, reason: str = 'None provided'):
       
        if not member.timed_out_until:
            await ctx.send(f'{emojis.alert} **{member}** is not timed out!')
            return
        try:
            await member.timeout(None, reason=reason)
        except discord.errors.Forbidden:
            await ctx.send(f'{emojis.alert} I do not have permission to untimeout this user')
            return
        
        bot_message = await ctx.send(f'{emojis.untimeout} **{member}** has been untimed out!')
        await utils.log_action(ctx, 'untimeout', member, ctx.guild, reason)
        await self.delete_messages(ctx, bot_message)

    @commands.hybrid_command()
    @utils.has_permission('warn')
    async def warn(self, ctx, member: discord.Member,*, reason: str = None):
        if not reason:
            await ctx.send(f'{emojis.alert} You must provide a reason')
            return
        if member == ctx.author:
            await ctx.send(f'{emojis.alert} You cant warn yourself!')
            return
        elif member.top_role >= ctx.author.top_role:
            await ctx.send(f'{emojis.alert} You cannot warn someone with the same or a higher role than you')
            return
        
        bot_message = await ctx.send(f'{emojis.warn} **{member}** has been warned. Reason: **{reason}**')
        await utils.log_action(ctx, 'warn', member, ctx.guild, reason)
        await self.delete_messages(ctx, bot_message)

    @commands.hybrid_command()
    @utils.has_permission('pardon')
    async def pardon(self, ctx, member: discord.Member, case_id: str = None,*, reason: str = 'None provided'):
        if not case_id:
            await ctx.send(f'{emojis.alert} You must provide a case ID')
            return
        case = await bot.find_one('moderation', {'_id': case_id, 'action': 'warn'})
        if not case:
            await ctx.send(f'{emojis.alert} Could not find this warn')
            return
        
        bot_message = await ctx.send(f'{emojis.pardon} **{member}** has been pardoned')
        await utils.log_action(ctx, 'pardon', member, ctx.guild, f'Pardoned case {case_id} | {reason}')
        await self.delete_messages(ctx, bot_message)


    @commands.hybrid_command()
    @utils.has_permission('manage_channel')
    async def purge(self, ctx, amount: int, user: discord.Member = None, type: str = 'all'):
        if amount > 200:
            await ctx.send(f'{emojis.alert} You cannot delete more than 200 messages at once')
            return
        
        await ctx.send(f'{emojis.trash} Deleting {amount} messages...', delete_after=3)

        def check(message):
            if user and message.author != user:
                return False
                
            if type.lower() == 'media':
                return len(message.attachments) > 0 or len(message.embeds) > 0
            elif type.lower() == 'text':
                return len(message.attachments) == 0 and len(message.embeds) == 0
            return True
        
        deleted = await ctx.channel.purge(limit=amount+2, check=check)
        await ctx.send(f'{emojis.trash} Deleted {len(deleted)} messages', delete_after=3)

        await utils.log_action(ctx, 'purge', ctx.author, ctx.guild, f'Deleted {len(deleted)} messages', channel_only=True)

async def setup(bot):  
    await bot.add_cog(ModerationCommands(bot))