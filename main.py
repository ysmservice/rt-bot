# RT

from ujson import load
import rtutil

print("Now loading...")

bot = rtutil.RTShardClient(command_prefix="r2!", log=True)


with open("data.json", "r") as f:
    bot.data = load(f)


@bot.event
async def on_ready():
    print("Connected")


@bot.event
async def on_message(message):
    await bot.run_command(message)

@bot.command()
async def test(ctx):
    await ctx.reply("test")

@bot.command()
async def test_worker(ctx):
    async def yey(ctx):
        await ctx.reply("From worker")
    await ctx.reply("From main")
    await bot.add_queue(yey, [ctx])


bot.run(bot.data["token"])
