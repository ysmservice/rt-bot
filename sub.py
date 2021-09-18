"""RT Backend (C) 2020 RT-Team
LICENSE : ./LICENSE
README  : ./readme.md
"""

desc = r"""
りつちゃん - (C) 2020 RT-Team
少女起動中..."""
print(desc)

from discord.ext import commands
import discord

from asyncio import sleep
from os import listdir
from sys import argv
import ujson
import rtlib

from data import data, is_admin


# 設定ファイルの読み込み。
with open("token.secret", "r", encoding="utf-8_sig") as f:
    secret = ujson.load(f)
TOKEN = secret["token"][argv[1]]


# その他設定をする。
prefixes = data["prefixes"][argv[1]]


# Backendのセットアップをする。
def setup(bot):
    bot.admins = data["admins"]

    bot.session = ClientSession(loop=bot.loop)
    @bot.listen()
    async def on_close(loop):
        await bot.session.close()
        del bot.mysql


    # エクステンションを読み込む。
    rtlib.setup(bot)
    bot.load_extension("jishaku")

    async def setting_up():
        await sleep(3)
        await bot.change_presence(
            activity=discord.Game(
                name="少女起動中..."
            ), status=discord.Status.dnd
        )

    bot._loaded = False

    @bot.event
    async def on_ready():
        # cogsフォルダにあるエクステンションを読み込む。
        if not bot._loaded:
            for name in ("cogs.tts", "cogs.music", "cogs._sub"):
                bot.load_extension(name)
            bot.dispatch("full_ready")
            bot._loaded = True

    bot.loop.create_task(setting_up())

# テスト時は普通のBackendを本番はシャード版Backendを定義する。
intents = discord.Intents.default()
intents.typing = False
intents.guild_typing = False
intents.dm_typing = False
intents.members = True
args = (prefixes,)
kwargs = {
    "help_command": None,
    "on_init_bot": on_init,
    "intents": intents
}
bot = commands.Bot(command_prefix=data[])
bot.test = False


server = (eval(argv[2]) if len(argv) > 2 else True)


bot.data = data
bot.colors = data["colors"]
bot.is_admin = is_admin


# jishakuの管理者かどうか確認するためのコルーチン関数を用意する。
async def _is_owner(user):
    return bot.is_admin(user.id)
bot.is_owner = _is_owner
del is_admin, _is_owner


bot.run(TOKEN)
