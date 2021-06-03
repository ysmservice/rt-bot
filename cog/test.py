# RT - Test Cog

import rtutil


class Test(metaclass=rtutil.Cog):
    def __init__(self, worker):
        self.worker = worker

    @rtutil.Cog.listener("message_create")
    async def on_message(self, ws, data):
        print(data["content"])

    @rtutil.Cog.command()
    async def test(self, ws, data, ctx):
        print(data["author"])


def setup(bot):
    bot.add_cog(Test(bot))
