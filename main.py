# RT

from ujson import load
import rtutil

print("Now loading...")

bot = rtutil.RTShardClient(log=True)


with open("data.json", "r") as f:
    bot.data = load(f)


@bot.add_event
async def on_ready():
    print("Connected")


@bot.add_event
async def on_message(message):
    print(message.content)
    if message.content == "r2!test":
        await message.channel.send("test")


bot.run(bot.data["token"])
