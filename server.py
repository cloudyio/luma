from fastapi import FastAPI, Depends, HTTPException, Header
from cogs.utilities.functions import functions
from pydantic import BaseModel
from discord.ext import commands
from fastapi.middleware.cors import CORSMiddleware
import httpx
import dotenv
from typing import Optional
import discord
from util.mongo import Mongo
import os
import asyncio
from async_timeout import timeout
from util.queue_manager import queue_manager

bot = None

app = FastAPI()
dotenv.load_dotenv()

bottoken = os.getenv('TOKEN')
mongo = Mongo('bot')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Token(BaseModel):
    oauth_token: str

class GuildInfoRequest(BaseModel):
    oauth_token: str
    guild_id: str

class NicknameUpdate(BaseModel):
    oauth_token: str
    guild_id: str
    nickname: str

@app.post("/check_guilds")
async def check_bot_guilds(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split("Bearer ")[1]
    
    if bot is None:
        raise HTTPException(status_code=500, detail="Bot is not initialized")

    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(
                "https://discord.com/api/users/@me/guilds",
                headers=headers
            )
            
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid Discord token")
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Discord API error: {response.text}"
                )
                
            user_guilds = response.json()

        bot_guilds = [str(guild.id) for guild in bot.guilds] 
        
        guilds = {
            "bot_in": [],    
            "bot_not_in": [],  
        }

        for guild in user_guilds:
            permissions = int(guild["permissions"])
            is_admin = guild["owner"] or (permissions & 0x8) == 0x8
            
            if not is_admin:
                continue  
                
            guild_id = guild["id"]  
            if guild_id in bot_guilds:
                guilds["bot_in"].append(guild)
            else:
                guilds["bot_not_in"].append(guild)

        return guilds

    except Exception as e:
        print(f"Error in check_guilds: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/guild_info")
async def get_guild_info(guild_id: str, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split("Bearer ")[1]

    if bot is None:
        raise HTTPException(status_code=500, detail="Bot is not initialized")
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(
                "https://discord.com/api/users/@me",
                headers=headers
            )
            
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid Discord token")
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Discord API error: {response.text}"
                )
                
            user_info = response.json()
            user_id = user_info["id"]
            
            guild = bot.get_guild(int(guild_id))
            if guild is None:
                raise HTTPException(status_code=404, detail="Guild not found")
            
            member = guild.get_member(int(user_id))
            if member is None:
                raise HTTPException(status_code=403, detail="User is not in the guild")
            
            is_owner = guild.owner_id == member.id
            is_admin = member.guild_permissions.administrator
            if not is_owner and not is_admin:
                raise HTTPException(status_code=403, detail="User does not have admin permissions")
            
            stats = await mongo.find_one('stats', {'_id': guild.id})
            if stats is None:
                raise HTTPException(status_code=404, detail="Stats not found for the guild")
            config = await mongo.find_one('config', {'_id': str(guild.id)})
            if config is None:
                raise HTTPException(status_code=404, detail="Config not found for the guild")

            bot_member = guild.get_member(bot.user.id)
            bot_nickname = bot_member.nick if bot_member else None

            guild_info = {
                "id": guild.id,
                "name": guild.name,
                "icon": guild.icon,
                "owner_id": guild.owner_id,
                "total_members": guild.member_count,
                "active_members": stats.get("active", 0),
                "messages_today": stats.get("messages_today", 0),
                "commands_used": stats.get("commands_used", 0),
                "modules": config.get("modules", []),
                "prefix": config.get("prefix", "!"),
                "nickname": bot_nickname,
            }

            return guild_info

    except Exception as e:
        print(f"Error in guild_info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/update_nickname")
async def update_nickname(data: NicknameUpdate):
    if not bot:
        raise HTTPException(status_code=500, detail="bot not initialized")

    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {data.oauth_token}"}
            response = await client.get(
                "https://discord.com/api/users/@me",
                headers=headers
            )
            
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid Discord token")
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Discord API error: {response.text}"
                )

            user_info = response.json()
            user_id = user_info["id"]
            
            guild = bot.get_guild(int(data.guild_id))
            if guild is None:
                raise HTTPException(status_code=404, detail="Guild not found")
            
            member = guild.get_member(int(user_id))
            if member is None:
                raise HTTPException(status_code=403, detail="User is not in the guild")
            
            is_owner = guild.owner_id == member.id
            is_admin = member.guild_permissions.administrator
            if not is_owner and not is_admin:
                raise HTTPException(status_code=403, detail="User does not have admin permissions")

        await queue_manager.add_task(
            "change_nickname",
            guild_id=data.guild_id,
            nickname=data.nickname
        )
        return {"message": "Nickname updated successfully"}
    except Exception as e:
        print(f"error changing nickname: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get_channels_and_roles/{guild_id}")
async def get_channels_and_roles(guild_id: str, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.split("Bearer ")[1]

    if bot is None:
        raise HTTPException(status_code=500, detail="Bot is not initialized")
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(
                "https://discord.com/api/users/@me",
                headers=headers
            )
            
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid Discord token")
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Discord API error: {response.text}"
                )

            user_info = response.json()
            user_id = user_info["id"]
            
            guild = bot.get_guild(int(guild_id))
            if guild is None:
                raise HTTPException(status_code=404, detail="Guild not found")
            
            member = guild.get_member(int(user_id))
            if member is None:
                raise HTTPException(status_code=403, detail="User is not in the guild")
            
            is_owner = guild.owner_id == member.id
            is_admin = member.guild_permissions.administrator
            if not is_owner and not is_admin:
                raise HTTPException(status_code=403, detail="User does not have admin permissions")
            
            channels = []
            for channel in guild.channels:
                if channel.type == discord.ChannelType.text:
                    channels.append({
                        "id": channel.id,
                        "name": channel.name,
                    })
            
            roles = []
            for role in guild.roles:
                roles.append({
                    "id": role.id,
                    "name": role.name,
                })

            return {
                "channels": channels,
                "roles": roles,
            }
    except Exception as e:
        print(f"error getting channels and roles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Hello World"}