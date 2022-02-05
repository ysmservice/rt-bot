# RTの基本データ。

from typing import Optional

from discord.ext import commands

from .voices import *


class Colors:
    normal = 0x0066ff
    unknown = 0x80989b
    error = 0xeb6ea5
    player = 0x2ca9e1
    queue = 0x007bbb


data = {
    "prefixes": {
        "test": [
            "r2!", "R2!", "r2.", "R2.",
            "りっちゃん２　", "りっちゃん2 ", "r2>"
        ],
        "production": [
            "rt!", "Rt!", "RT!", "rt.", "Rt.",
            "RT.", "りつ！", "りつ."
        ],
        "sub": [
            "rt#", "りつちゃん ", "りつたん ", "りつ ",
            "りつちゃん　", "りつたん　", "りつ　", "Rt#", "RT#"
        ],
        "alpha": ["r3!", "r3>"]
    },
    "colors": {name: getattr(Colors, name) for name in dir(Colors)},
    "admins": [
        634763612535390209, 266988527915368448,
        667319675176091659, 693025129806037003
    ]
}


RTCHAN_COLORS = {
    "normal": 0xa6a5c4,
    "player": 0x84b9cb,
    "queue": 0xeebbcb
}
