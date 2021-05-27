# RT

from ujson import load
import rtutil


print("Now loading...")


client = rtutil.RTShardClient()


with open("data.json", "r") as f:
    client.data = load(f)


@client.event
async def on_ready():
    print("Connected")


print("Connecting...")
client.run(client.data["token"])
