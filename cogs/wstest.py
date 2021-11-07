# RT - WebSocket Test

from discord.ext import commands

from rtlib import RT, websocket


class WebSocketTest(commands.Cog):
    def __init__(self, bot: RT):
        self.bot = bot

    @websocket.websocket("/wstest", auto_connect=False, reconnect=False)
    async def test_websocket(self, ws: websocket.WebSocket, _):
        await ws.send("print", "From bot")
        await ws.send("ping")

    @test_websocket.event("ping")
    async def ping(self, _, data: websocket.PacketData):
        print("From backend:", data)

    @commands.command()
    async def start(self, ctx: commands.Context):
        await ctx.trigger_typing()
        try:
            await self.test_websocket.connect()
        except websocket.ConnectionFailed:
            await ctx.reply(
                "Failed to connect to the backend."
            )
        else:
            await ctx.reply(
                f"From backend: {await self.ping.wait()}"
            )
            await self.test_websocket.close()


def setup(bot):
    bot.add_cog(WebSocketTest(bot))