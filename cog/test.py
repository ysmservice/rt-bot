# RT - Test Cog

import rtutil


class Test(metaclass=rtutil.Cog):
    def __init__(self, bot):
        self.bot = bot

    @rtutil.Cog.listener("message_create")
    async def on_message(self, ws, data):
        print(data["content"])


def setup(bot):
    bot.add_cog(Test(bot))
