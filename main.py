# RT

from ujson import load
from rtutil import commands

print("Now loading...")

bot = commands.RTShardClient(log=True)


with open("data.json", "r") as f:
    bot.data = load(f)


@bot.event
async def on_ready():
	print("Connected")


bot.run(bot.data["token"])
