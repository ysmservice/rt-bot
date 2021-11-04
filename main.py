# RT Backend

from sanic.log import logger
from discord import Intents

from importlib import import_module
from ujson import load, dumps
from os import listdir

from utils import NewSanic, TypedBot


with open("auth.json", "r") as f:
    secret = load(f)


def on_setup(bot: TypedBot) -> None:
    # 拡張やBlueprintを読み込む。
    bot.load_extension("jishaku")
    for name in listdir("cogs"):
        if not name.startswith("_"):
            try:
                bot.load_extension(f"cogs.{name if '.' in name else name[:-3]}")
            except Exception as e:
                logger.warning(f"Failed to load the extension : {e}")
            else:
                logger.info(f"Loaded extension : {name}")
    for name in listdir("blueprints"):
        if not name.startswith("_"):
            module = import_module(f"blueprints.{name}")
            if hasattr(module, "bp"):
                bot.app.blueprint(module.bp)
                logger.info(f"Loaded blueprint : {name}")


app = NewSanic(
    (), dict(intents=Intents(messages=False), max_messages=100),
    secret["token"], True, on_setup, (), secret["mysql"],
    "RT-Backend", dumps=dumps
)


app.run(
    secret["app"]
)