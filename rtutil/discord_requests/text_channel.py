# RT - Discord Requests TextChannel


async def trigger_typing(self, ws, cache):
    await cache["channel"].trigger_typing()

async def history(self, ws, cache, *args, **kwargs):
    async for message in target.history(*args, **kwargs):
        await ws.send()
