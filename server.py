from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel
from discord.ext import commands
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Optional

bot = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Token(BaseModel):
    oauth_token: str

@app.post("/check_guilds")
async def check_bot_guilds(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        print("Invalid auth header:", authorization)
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.split("Bearer ")[1]
    
    if bot is None:
        print("Bot not initialized")
        raise HTTPException(status_code=500, detail="Bot is not initialized")

    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(
                "https://discord.com/api/users/@me/guilds",
                headers=headers
            )
            
            print(f"Discord API Response: {response.status_code}")
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid Discord token")
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Discord API error: {response.text}"
                )
                
            user_guilds = response.json()
            print(f"User Guilds: {len(user_guilds)}")

        bot_guilds = [str(guild.id) for guild in bot.guilds] 
        print(f"Bot Guilds: {len(bot_guilds)}")
        
        guilds = {
            "bot_in": [],    
            "bot_not_in": [],  
        }

        for guild in user_guilds:
            permissions = int(guild["permissions"])
            is_admin = guild["owner"] or (permissions & 0x8) == 0x8
            
            if not is_admin:
                continue  
                
            guild_id = guild["id"]  # Keep as string
            if guild_id in bot_guilds:
                guilds["bot_in"].append(guild)
            else:
                guilds["bot_not_in"].append(guild)

        print(f"Final Response: bot_in: {len(guilds['bot_in'])}, bot_not_in: {len(guilds['bot_not_in'])}")
        return guilds

    except Exception as e:
        print(f"Error in check_guilds: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/guild_info")
async def get_guild_info(token: Token, guild_id: str):
    if bot is None:
        raise HTTPException(status_code=500, detail="Bot is not initialized")
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bot {token.oauth_token}"}
            response = await client.get(
                f"https://discord.com/api/guilds/{guild_id}",
                headers=headers
            )
            
            if response.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid Discord token")
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Discord API error: {response.text}"
                )
                
            guild = response.json()
            print(f"Guild: {guild}")
            return guild

    except Exception as e:
        print(f"Error in guild_info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "Hello World"}