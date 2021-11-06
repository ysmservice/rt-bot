# RT - WebSocket Test

from typing import TYPE_CHECKING

from discord.ext import commands

from rtlib import RT, websocket, WebSocket, PacketData


class WebSocketTest(commands.Cog):
    def __init__(self, bot: RT):
        self.bot = bot

    @websocket("/wstest")
    async def test_websocket(self, ws: WebSocket, _):
        await ws.send("print", "From bot")
        await ws.send("ping")

    @test_websocket.event("ping")
    async def test_websocket(self, _, data: PacketData):
        print("From backend:", data)


def setup(bot)