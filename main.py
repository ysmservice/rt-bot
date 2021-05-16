# RT

from ujson import load
from util import shard


bot = shard.RTShardClient(5)

with open("data.json", "r") as f:
    bot.data = load(f)


bot.run(bot.data["token"])
