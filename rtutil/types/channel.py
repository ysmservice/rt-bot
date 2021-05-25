# RT - Types Channel

from .guild import *
from .message import *
from ujson import loads, dumps


class BaseChannel:
    def __init__(self, ws, data):
        self.ws = ws

        self.id = data["id"]
        self.guild = Guild(ws, data)
        self.name = data["name"]
        self.category_id = data["category_id"]
        self.position = data["position"]


class TextChannel(BaseChannel):
    def __init__(self, ws, data):
        super().__init__(ws, data)
        self.ws, data = ws, data

        self.topic = data["topic"]
        self.last_message_id = data["last_message_id"]
        self.slowmode_delay = data["slowmode_delay"]
        self.nsfw = data["nsfw"]

    async def history(self, *args, **kwargs):
        data = {
            "type": "history",
            "data": {"target": self.id, "args": args, "kwargs": kwargs}
        }
        await self.ws.send(dumps({"type": "discord_iter", "data": data}))
        while True:
            data = loads(await self.ws.recv())
            await self.ws.send(dumps({"type": "ok", "data": {}}))
            if data["type"] == "ok":
                break
            yield Message(self.ws, data["data"])

    async def typing(self):
        data = {"type": "trigger_typing", "data": {"target": self.id}}
        await self.ws.send(dumps({"type": "discord", "data": data}))
        await self.ws.recv()

    async def trigger_typing(self):
        await self.typing()
