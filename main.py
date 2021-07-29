"""RT Backend
(C) 2020 RT-Team
起動方法はREADME.mdを参照してください。"""

from sys import argv
import ujson
import rtlib

from data import data, is_admin
import rtutil


# 設定ファイルの読み込み。
with open("token.secret", "r", encoding="utf-8_sig") as f:
    secret: dict = ujson.load(f)
TOKEN = secret["token"][argv[1]]


# その他設定をする。
prefixes = data["prefixes"][argv[1]]


# Backendのセットアップをする。
def on_init(bot):
    bot.data["mysql"] = rtutil.mysql.MySQLManager(
        bot.loop, secret["mysql"]["user"], secret["mysql"]["password"])
    bot.is_owner = lambda user: bot.is_admin(user.id)

    bot.load_extension("jishaku")
    bot.load_extension("rtlib.libs.on_full_reaction")
    bot.load_extension("rtlib.libs.on_command_add")
    bot.load_extension("cogs.database")


bot = rtlib.Backend(command_prefix=prefixes,
                    on_init_bot=on_init)
bot.data = data
bot.is_admin = is_admin
del is_admin


bot.run(TOKEN, host="0.0.0.0", port=80)
