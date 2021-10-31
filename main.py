"""RT Backend (C) 2020 RT-Team
LICENSE : ./LICENSE
README  : ./readme.md
"""

desc = """
  _____ _______   _____  _                       _   ____        _
 |  __ \\__   __| |  __ \\(_)                     | | |  _ \\      | |
 | |__) | | |    | |  | |_ ___  ___ ___  _ __ __| | | |_) | ___ | |_
 |  _  /  | |    | |  | | / __|/ __/ _ \\| '__/ _` | |  _ < / _ \\| __|
 | | \\ \\  | |    | |__| | \\__ \\ (_| (_) | | | (_| | | |_) | (_) | |_
 |_|  \\_\\ |_|    |_____/|_|___/\\___\\___/|_|  \\__,_| |____/ \\___/ \\__|
Now loading..."""
print(desc)

from aiohttp import ClientSession
from asyncio import sleep
from os import listdir
from sys import argv
import discord
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
def on_init(bot):
    bot.admins = data["admins"]

    bot.session = ClientSession(loop=bot.loop)
    @bot.listen()
    async def on_close(loop):
        await bot.session.close()
        del bot.mysql

    bot.mysql = bot.data["mysql"] = rtlib.mysql.MySQLManager(
        loop=bot.loop, user=secret["mysql"]["user"],
        password=secret["mysql"]["password"], db="mysql",
        pool = True, minsize=1, maxsize=50 if bot.test else 1000,
      autocommit=True
    )
    oauth_secret = secret["oauth"][argv[1]]
    bot.oauth = bot.data["oauth"] = rtlib.OAuth(
        bot, oauth_secret["client_id"], oauth_secret["client_secret"],
        oauth_secret["client_secret"]
    )
    bot.secret = secret
    bot.oauth_secret = secret["oauth"][argv[1]]
    del oauth_secret

    # エクステンションを読み込む。
    rtlib.setup(bot)
    bot.load_extension("jishaku")
    bot.load_extension("rtutil.oauth_manager")
    bot.load_extension("rtutil.setting_api")

    async def setting_up():
        await sleep(3)
        await bot.change_presence(
            activity=discord.Game(
                name="起動準備"
            ), status=discord.Status.dnd
        )

    bot._loaded = False

    @bot.event
    async def on_ready():
        # cogsフォルダにあるエクステンションを読み込む。
        if not bot._loaded:
            for path in listdir("cogs"):
                if path[0] in ("#", ".", "_"):
                    continue
                try:
                    if path.endswith(".py"):
                        bot.load_extension("cogs." + path[:-3])
                    elif "." not in path and path != "__pycache__" and path[0] != ".":
                        bot.load_extension("cogs." + path)
                except discord.ext.commands.NoEntryPointError as e:
                    if "setup" not in str(e):
                        raise e
                bot.print("Loaded extension", path)
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
    "intents": intents,
    "allowed_mentions": discord.AllowedMentions(
        everyone=False, users=False
    )
}
if argv[1] in ("test", "alpha"):
    bot = rtlib.Backend(*args, **kwargs)
    bot.test = True
elif argv[1] == "production":
    bot = rtlib.AutoShardedBackend(*args, **kwargs)
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


bot.run(
    TOKEN, host="0.0.0.0" if server else "127.0.0.1",
    port=80 if server else 5500
)
