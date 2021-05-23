# RT - d.py

import discord


class DiscordFunctions():
    def __init__(self, bot):
        self.bot = bot

    async def send(self, channel_id, *args, **kwargs):
        channel = self.bot.get_channel(channel_id)
        if channel:
            await channel.send(*args, **kwargs)
        else:
            raise ValueError("チャンネルが見つかりませんでした。")
