import os
import logging
from discord.ext import commands
import discord
import threading
from dotenv import load_dotenv
import uvicorn
from server import app
import server
import util.mongo as mongo
import globals
from util.queue_manager import queue_manager  # Add this import

load_dotenv()
TOKEN = os.getenv('TOKEN')
ENVIRONMENT = os.getenv('ENVIRONMENT')

if ENVIRONMENT == 'production':
    level = logging.WARNING
else:
    level= logging.INFO

logging.basicConfig(
    level=level,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def start_server():
    uvicorn.run(app, host="localhost", port=8000)

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        intents.messages = True
        if ENVIRONMENT != 'production':
            intents.guilds = True

        super().__init__(command_prefix="!", intents=intents)
        self.bg_task = None

    async def on_ready(self):
        server.bot = self
        self.bg_task = self.loop.create_task(self.process_discord_queue())
        logger.warning(f'Logged in as {self.user} (ID: {self.user.id}) PROD ENVIRONMENT')
        logger.warning('------')
        
    if ENVIRONMENT != 'production':
        from cogwatch import watch
        @watch(path='cogs', preload=True) 
        async def on_ready(self):
            server.bot = self
            self.bg_task = self.loop.create_task(self.process_discord_queue())
            logger.info(f'Logged in as {self.user} (ID: {self.user.id}) DEV ENVIRONMENT')
            logger.info('------')
      
        
    async def setup_hook(self):
        await mongo.check_status()
        await self.load_cogs()

    async def load_cogs(self):
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f'Loaded cog: {filename}')
                except Exception as e:
                    logger.error(f'Failed to load cog {filename}: {e}')      


    async def cleanup_logs(self, max_lines=100):
        log_path = "bot.log"

        try:
            with open(log_path, "r") as file:
                lines = file.readlines()

            if len(lines) > max_lines:
                with open(log_path, "w") as file:
                    file.writelines(lines[-max_lines:])
                logger.info(f"Trimmed log file to the last {max_lines} lines.")
        except Exception as e:
            logger.error(f"Error cleaning up log file: {e}")  

    async def process_discord_queue(self):
        while True:
            try:
                task = await queue_manager.get_task()
                if task.action == "change_nickname":
                    try:
                        guild = self.get_guild(int(task.params['guild_id']))
                        if guild:
                            bot_member = guild.get_member(self.user.id)
                            if bot_member:
                                await bot_member.edit(nick=task.params['nickname'])
                                task.future.set_result(True)
                            else:
                                task.future.set_exception(Exception("Bot not found in guild"))
                        else:
                            task.future.set_exception(Exception("Guild not found"))
                    except Exception as e:
                        task.future.set_exception(e)
                queue_manager.task_done()
            except Exception as e:
                print(f"Error processing queue: {e}")
                await asyncio.sleep(1)

    async def close(self):
        if self.bg_task:
            self.bg_task.cancel()
        await self.cleanup_logs()
        await super().close()

async def main():
    bot = Bot()
    
    threading.Thread(target=start_server, daemon=True).start()
    await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
