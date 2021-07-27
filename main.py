# RT Backend

from sys import argv
import ujson
import rtlib


# 設定ファイルの読み込み。
with open("data.json", "r", encoding="utf-8_sig") as f:
    data: dict = ujson.load(f)
with open("token.secret", "r", encoding="utf-8_sig") as f:
    tokens: list = f.read().splitlines()
TOKEN = tokens[2] if argv[1] == "production" else tokens[1]


# その他設定をする。
prefixes = data["prefixes"][argv[1]]


# Backendのセットアップをする。
def on_init(bot):
    bot.load_extension("jishaku")
    bot.rtlibs.append("on_full_reaction")


bot = rtlib.Backend(command_prefix=prefixes,
                    on_init_bot=on_init)
bot.data = data


bot.run(TOKEN)
