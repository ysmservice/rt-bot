"""RT Backend (C) 2020 RT-Team
LICENSE : ./LICENSE
README  : ./readme.md
"""

from asyncio import coroutine
from sys import argv
import ujson
import rtlib

from data import data, is_admin


# 設定ファイルの読み込み。
with open("token.secret", "r", encoding="utf-8_sig") as f:
    secret: dict = ujson.load(f)
TOKEN = secret["token"][argv[1]]


# その他設定をする。
prefixes = data["prefixes"][argv[1]]


# Backendのセットアップをする。
def on_init(bot):
    bot.data["mysql"] = rtlib.mysql.MySQLManager(
        bot.loop, secret["mysql"]["user"], secret["mysql"]["password"])

    # エクステンションを読み込む。
    bot.load_extension("jishaku")
    bot.load_extension("rtlib.libs.on_full_reaction")
    bot.load_extension("rtlib.libs.on_command_add")
    bot.load_extension("rtlib.libs.dochelp")
    bot.load_extension("cogs.database")


# テスト時は普通のBackendを本番はシャード版Backendを定義する。
args = (prefixes,)
kwargs = {
    "help_command": None,
    "on_init_bot": on_init
}
if argv[1] == "test":
    bot = rtlib.Backend(*args, **kwargs)
elif argv[1] == "production":
    bot = rtlib.AutoShardedBackend(*args, **kwargs)
bot.data = data
bot.is_admin = is_admin


# jishakuの管理者かどうか確認するためのコルーチン関数を用意する。
async def _is_owner(user):
    return bot.is_admin(user.id)
bot.is_owner = _is_owner
del is_admin, _is_owner


bot.run(TOKEN, host="0.0.0.0", port=80)
