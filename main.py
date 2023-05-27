import discord
from discord.ext import commands
import os
import asyncio
# from dotenv import load_dotenv
# load_dotenv()


intents = discord.Intents.default()
intents.message_content = True

# botのオブジェクトを作成
bot: commands.Bot = commands.Bot(
    command_prefix="/",
    intents=discord.Intents.all(),
    application_id=os.getenv("APPLICATION_ID"),
)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')


async def main():
    cogfolder = "cogs."
    cogs = ["main_cog"]
    for cog in cogs:
        await bot.load_extension(cogfolder + cog)
    await bot.tree_sync()

    async with bot:
        # Botのトークンを指定（Developer Portalで確認可能）
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

asyncio.run(main())
