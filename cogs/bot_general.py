# RT - Bog General

from discord.ext import commands, tasks
import discord

from time import time


class BotGeneral(commands.Cog):

    STATUS_TEXTS = (
        ("{}help | {} servers", lambda bot: len(bot.guilds)),
        ("{}help | {} users", lambda bot: len(bot.users))
    )

    def __init__(self, bot):
        self.bot, self.rt = bot, bot.data

        self._now_status_index = 0
        self._start_time = time()
        self.status_updater.start()

    def _get_ping(self) -> int:
        # pingを返します。
        return round(self.bot.latency * 1000)

    def cog_unload(self) -> None:
        self.status_updater.cancel()

    @tasks.loop(seconds=60)
    async def status_updater(self) -> None:
        # RTのステータスを更新するループです。
        await self.bot.wait_until_ready()

        await self.bot.change_presence(
            activity=discord.Activity(
                name=(now := self.STATUS_TEXTS[self._now_status_index])[0]
                    .format(self.bot.command_prefix[0], now[1](self.bot)),
                type=discord.ActivityType.watching, state="RT Discord Bot",
                details=f"PING：{self._get_ping()}\n絶賛稼働中...",
                timestamps={"start": self._start_time},
                buttons={"label": "RTのホームページに行く！", "url": "https://rt-bot.com/"}
            )
        )

        self._now_status_index = 0 if self._now_status_index else 1

    @commands.command(
        extras={
            "headding": {
                "ja": "レイテンシを表示します。",
                "en": "Show you RT latency."
            },
            "parent": "RT"
        }
    )
    async def ping(self, ctx):
        """!lang ja
        --------
        RTのレイテンシを表示します。  
        返信された数字が400以降だとネット回線が悪いです。

        !lang en
        --------
        You can view RT latency.  
        If latency is over to 400, network is bad."""
        await ctx.reply(f"現在のRTのレイテンシ：${self._get_ping()}$ms")

    async def _setting_test_callback(self, ctx, data):
        print(ctx.author.name, data)

    @commands.command(
        extras={
            "on_setting": {
                "description": "テスト設定。",
                "callback": _setting_test_callback,
                "mode": "guild",
                "items": [
                    {
                        "permissions": ["administrator"],
                        "item_type": "text",
                        "name": "引数1",
                        "text": "デフォルトのテキスト"
                    }
                ]
            }
        }
    )
    async def _setting_test(self, ctx, *, text):
        await self._setting_test_callback(ctx, text)
        await ctx.reply("Ok")


def setup(bot):
    bot.add_cog(BotGeneral(bot))
