"""RT Backend
(C) 2020 RT-Team
起動方法はREADME.mdを参照してください。"""

from sys import argv
import ujson
import rtlib


# 設定ファイルの読み込み。
with open("data.json", "r", encoding="utf-8_sig") as f:
    data: dict = ujson.load(f)
with open("token.secret", "r", encoding="utf-8_sig") as f:
    tokens: dict = ujson.load(f)
TOKEN = tokens["token"][argv[1]]


# その他設定をする。
prefixes = data["prefixes"][argv[1]]


# Backendのセットアップをする。
def on_init(bot):
    bot.load_extension("jishaku")
    bot.load_extension("rtlib.libs.on_full_reaction")
    bot.load_extension("rtlib.libs.on_command_add")


bot = rtlib.Backend(command_prefix=prefixes,
                    on_init_bot=on_init)
bot.data = data


bot.run(TOKEN, host="0.0.0.0", port=80)
