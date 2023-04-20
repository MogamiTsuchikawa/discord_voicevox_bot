import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
# load_dotenv()


intents = discord.Intents.default()
intents.message_content = True

# botのオブジェクトを作成(コマンドのトリガーを!に)
bot = commands.Bot(
    command_prefix="/",
    intents=discord.Intents.all(),
    application_id=os.getenv("APPLICATION_ID"),
    # activity=discord.Activity(name="準備中")
)


@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')


async def main():
    cogfolder = "cogs."
    cogs = ["main_cog"]
    for cog in cogs:
        await bot.load_extension(cogfolder+cog)
    await bot.tree_sync()

    async with bot:
        # Botのトークンを指定（デベロッパーサイトで確認可能）
        await bot.start(os.getenv("DISCORD_BOT_TOKEN"))

asyncio.run(main())
