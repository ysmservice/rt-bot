# RTの基本データ。

from discord.ext import commands
from .voices import *


data = {
    "prefixes": {
        "test": [
            "r2!", "R2!", "r2.", "R2.",
            "りっちゃん２　", "りっちゃん2 ", "r2>"
        ],
        "production": [
            "rt!", "Rt!", "RT!", "rt.", "Rt.",
            "RT.", "りつ！", "りつ.", "りっちゃん　",
            "りっちゃん ", "りつちゃん ", "りつちゃん　"
        ],
        "alpha": ["r3!", "r3>"]
    },
    "colors": {
        "normal": 0x0066ff,
        "unknown": 0x80989b,
        "error": 0xeb6ea5
    },
    "admins": [
        634763612535390209, 266988527915368448,
        667319675176091659, 693025129806037003
    ]
}


HEADERS = {
    "Access-Control-Allow-Origin": "https://rt-bot.com",
    "Access-Control-Allow-Credentials": "true"
}
TEST_HEADERS = {
    "Access-Control-Allow-Origin": "http://127.0.0.1:5500",
    # "Access-Control-Allow-Origin": "http://192.168.1.14",
    "Access-Control-Allow-Credentials": "true"
}
def get_headers(bot, request) -> dict:
    # 上のものを取得する関数です。
    if bot.test:
        headers = TEST_HEADERS
        if "192.168.1.14" in request.url:
            headers["Access-Control-Allow-Origin"] = "http://192.168.1.14"
        elif "127.0.0.1" in request.url:
            headers["Access-Control-Allow-Origin"] = "http://127.0.0.1:5500"
        elif "tasuren" in request.url:
            headers["Access-Control-Allow-Origin"] = "http://tasuren.f5.si:5500"
        else:
            headers["Access-Control-Allow-Origin"] = "http://localhost:5500"
    else:
        headers = HEADERS
    return headers


def is_admin(user_id=None):
    def check(ctx):
        if isinstance(user_id, int):
            return user_id in data["admins"]
        else:
            return ctx.author.id in data["admins"]
    if user_id is None:
        return commands.check(check)
    else:
        return check(user_id)
