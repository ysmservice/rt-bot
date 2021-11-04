# RT Backend

from sanic.log import logger
from discord import Intents

from ujson import load, dumps
from os import listdir

from utils import NewSanic, TypedBot


with open("auth.json", "r") as f:
    secret = load(f)


def on_setup(bot: TypedBot) -> None:
    bot.load_extension("jishaku")
    for name in listdir("cogs"):
        if not name.startswith("_"):
            try:
                bot.load_extension(f"cogs.{name if '.' in name else name[:-3]}")
            except Exception as e:
                logger.warning(f"Failed to load the extension : {e}")
            else:
                logger.info(f"Loaded extension : {name}")


app = NewSanic(
    (), dict(intents=Intents(messages=False), max_messages=100),
    secret["token"], True, on_setup, (), secret["mysql"],
    "RT-Backend", dumps=dumps
)


app.run(
    secret["app"]
)