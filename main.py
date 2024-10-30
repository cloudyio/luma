import os
import logging
from discord.ext import commands
import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TOKEN')
ENVIRONMENT = os.getenv('ENVIRONMENT')

if ENVIRONMENT == 'production':
    level = logging.WARNING
else:
    level = logging.INFO

logging.basicConfig(
    level=level,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        if ENVIRONMENT != 'production':
            intents.guilds = True

        super().__init__(command_prefix="!", intents=intents)

    async def on_ready(self):
        logger.warning(f'Logged in as {self.user} (ID: {self.user.id}) PROD ENVIRONMENT')
        logger.warning('------')

    if ENVIRONMENT != 'production':
        from cogwatch import watch
        @watch(path='cogs', preload=True) 
        async def on_ready(self):
            logger.info(f'Logged in as {self.user} (ID: {self.user.id}) DEV ENVIRONMENT')
            logger.info('------')
      
        
    async def setup_hook(self):
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

    async def close(self):
        await self.cleanup_logs()
        await super().close()

    

async def main():
    bot = Bot()
    await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
