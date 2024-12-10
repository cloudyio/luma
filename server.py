from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class GuildCheckRequest(BaseModel):
    guild_ids: list[int]

check_guilds = None

def init_server(check_guilds_func):
    global check_guilds
    check_guilds = check_guilds_func

@app.post("/check_guilds")
async def check_bot_guilds(request: GuildCheckRequest):
    if check_guilds:
        guilds_in_bot = await check_guilds(request.guild_ids)
        return {"guilds_in_bot": guilds_in_bot}
    return {"error": "Bot function not set"}

@app.get("/")
async def root():
    return {"message": "Hello World"}