# RT - Bog General

from discord.ext import commands, tasks
import discord

from time import time
from rtutil import SettingManager


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

    async def _setting_test_callback(self, ctx, mode, items):
        if mode == "read":
            for item_name in items:
                yield "既に設定されてる値。"
        else:
            for item_name, content in items:
                print("設定更新後 :", content)

    @commands.command()
    @SettingManager.setting(
        "guild", "テスト用設定", {
            "ja": "設定のテストを行うためのものです。",
            "en": "Test setting item."
        },
        ["administrator"], _setting_test_callback,
        {"text:box_1": {"ja": "テスト", "en": "test"}})
    async def _setting_test(self, ctx, *, text):
        await self._setting_test_callback(ctx, "write", (("box_1", "New"),))
        await ctx.reply("Ok")

    async def _setting_test_user_callback(self, ctx, mode, items):
        if mode == "read":
            for item_name in items:
                if item_name.startswith("text"):
                    yield "デフォルトの値"
                elif item_name.startswith("radios"):
                    yield {"radio1": False, "radio2": True}
        else:
            for item_name, content in items:
                print("設定更新後：", content)

    @commands.command()
    @SettingManager.setting(
        "user", "テスト用ユーザー設定", "Foo↑", [], _setting_test_user_callback,
        {"text:box_1": "Yey", "radios:radios_1": "radios"})
    async def _setting_test_user(self, ctx):
        await self._setting_test_callback(ctx, "write", (("box_1", "New"), ("radios_1", {"radio1": False, "radio2": True})))


def setup(bot):
    bot.add_cog(BotGeneral(bot))
