import discord
from discord.ext import commands
from util.utils import emojis, has_permission, Pagnination
from util.mongo import Mongo

bot_db = Mongo('bot')

class Visual(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    @commands.hybrid_command(name='case', description='Find a case by ID')
    @has_permission('moderator')
    async def case(self, ctx, case_id: str):
        case = await bot_db.find_one('moderation', {'_id': case_id})
        if not case:
            return await ctx.send(f'{emojis.alert} Case not found')
        
        user = ctx.guild.get_member(case['user'])
        if not user:
            user = await self.bot.fetch_user(case['user'])
            if not user:
                return await ctx.send(f"{emojis.alert} User doesn't exist anymore!")
        
        color_map = {
            'ban': 0xFF0000,    
            'unban': 0x00FF00,  
            'kick': 0xFFA500,   
            'timeout': 0xFFFF00,
            'untimeout': 0x00FF00, 
            'warn': 0xFFD700,  
            'pardon': 0x00FF00    
        }
        
        action_emoji = getattr(emojis, case['action'], '')
        
        embed = discord.Embed(
            title=f"{action_emoji} Case {case['_id']}",
            color=color_map.get(case['action'], 0x7289DA)
        )
        
        embed.add_field(
            name="Action", 
            value=case['action'].upper(), 
            inline=True
        )
        embed.add_field(
            name="User", 
            value=f"{user.mention}\n({user.name})", 
            inline=True
        )
        embed.add_field(
            name="User ID", 
            value=f"```{user.id}```", 
            inline=True
        )
        embed.add_field(
            name="Reason", 
            value=f"```{case['reason']}```", 
            inline=False
        )
        
        moderator = ctx.guild.get_member(case['moderator'])
        if not moderator:
            moderator = await self.bot.fetch_user(case['moderator'])
        
        embed.add_field(
            name="Moderator",
            value=f"{moderator.mention}\n({moderator.name})" if moderator else "Unknown Moderator",
            inline=False
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.timestamp = case['timestamp']
        embed.set_footer(text=f"Case ID: {case['_id']}")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name='cases', description='Find all cases for a user')
    @has_permission('moderator')
    async def cases(self, ctx, user: discord.User):
        cases = await bot_db.find('moderation', {'user': int(user.id), 'guild': int(ctx.guild.id)})
        if not cases:
            return await ctx.send(f'{emojis.alert} No cases found for this user')
        
        cases.sort(key=lambda x: x['timestamp'], reverse=True)
        
        pages = []
        for i in range(0, len(cases), 5):
            page_cases = cases[i:i + 5]
            embed = discord.Embed(
                title=f"Moderation History",
                description=f"Showing cases for {user.mention} ({user.name})",
                color=0x7289DA 
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            
            for case in page_cases:
                action_emoji = getattr(emojis, case['action'], '')
                timestamp = discord.utils.format_dt(case['timestamp'], style='R')
                formatted_date = discord.utils.format_dt(case['timestamp'], style='D')
                
                moderator = ctx.guild.get_member(case['moderator'])
                if not moderator:
                    moderator = await self.bot.fetch_user(case['moderator'])
                mod_text = f"{moderator.name}" if moderator else "Unknown Moderator"
                
                embed.add_field(
                    name=f"{action_emoji} Case {case['_id']} • {case['action'].upper()}",
                    value=f"**When:** {formatted_date} ({timestamp})\n**Moderator:** {mod_text}\n**Reason:** {case['reason'][:250]}",
                    inline=False
                )
            
            embed.set_footer(text=f"Page {i//5 + 1}/{-(-len(cases)//5)}")
            pages.append(embed)
        
        view = Pagnination(pages)
        view.current.label = f"1/{len(pages)}"
        view.message = await ctx.send(embed=pages[0], view=view)

        
async def setup(bot):  
    await bot.add_cog(Visual(bot))