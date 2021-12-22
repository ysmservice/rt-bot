# RT Captcha - Word

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from .__init__ import Captcha


class WordCaptcha:
    def __init__(self, cog: "Captcha"):
        self.cog = cog

    async def on_message(self, message: discord.Message):
        if (message.channel.id == self.cog.queue[message.guild.id] \
            [message.author.id][2].extras["data"]["channel_id"]
                and message.content == self.cog.queue[message.guild.id] \
            [message.author.id][2].extras["data"]["word"]):
            await message.delete()
            await message.channel.send(f"{message.author.mention}, 認証に成功しました。")
            await self.cog.remove_queue(message.guild.id, message.author.id)
        else:
            await message.reply("合言葉が違います。")