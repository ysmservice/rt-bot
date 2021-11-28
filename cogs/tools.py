# RT - Tools For Dashboard

from typing import Literal

from discord.ext import commands
import discord

from rtlib.setting import Context, Setting
from rtlib import RT

from asyncio import sleep


class Tools(commands.Cog):
    def __init__(self, bot: RT):
        self.bot = bot

    @commands.group("settest")
    async def setting_test(self, ctx: Context):
        if not ctx.invoked_subcommand:
            await ctx.reply("...")

    @setting_test.command(
        aliases=["stc"], headding={
            "ja": "メッセージを特定のチャンネルに送信します。", "en": "Send message"
        }
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.channel)
    @Setting("guild", "send", channel=discord.TextChannel)
    async def send_(self, ctx: Context, *, content: str):
        await ctx.channel.send(content)
        await ctx.reply(f"{ctx.channel.name}にメッセージを送信しました。")

    @commands.command(
        headding={
            "ja": "IDチェッカー", "en": "ID Checker"
        }, parent="Individual"
    )
    @Setting("user")
    async def checker(self, ctx):
        await ctx.reply(f"あなたのIDは`{ctx.author.id}`です。")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.guild)
    @Setting("Tools", "Loading表示")
    async def setting_test_loading(self, ctx: Context, number: Literal[1, 2, 3, 4, 5]):
        await sleep(number)
        await ctx.reply("Loading楽しかった？")

    OKES = ["+", "-", "*", "/", "."]
    OKCHARS = list(map(str, range(9))) + OKES

    def safety(self, word):
        return "".join(char for char in str(word) if char in self.OKCHARS)

    @commands.command(
        headding={
            "ja": "式を入力して計算を行うことができます。", "en": "Calculation by expression"
        }, parent="Individual"
    )
    @Setting("Tools", "簡易電卓")
    async def calc(
        self, ctx: Context, *, expression: str
    ):
        if len(expression) < 400:
            await ctx.reply(f"計算結果：`{eval(self.safety(expression))}`")
        else:
            raise commands.BadArgument("計算範囲が大きすぎます！頭壊れます。")

    @commands.command(
        headding={
            "ja": "文字列を逆順にします。", "en": "Reverse text"
        },
        parent="Individual"
    )
    @Setting("Tools", "文字列逆順")
    async def reverse(self, ctx: Context, *, bigbox):
        await ctx.reply(f"結果：\n```\n{bigbox[::-1]}\n```")

    @commands.command(
        headding={
            "ja": "文字列の交換を行います。", "en": "Replace text"
        }, parent="Individual"
    )
    @Setting("Tools", "文字列交換")
    async def replace(self, ctx: Context, before, after, *, text):
        await ctx.reply(f"結果：{text.replace(before, after)}")


def setup(bot):
    bot.add_cog(Tools(bot))