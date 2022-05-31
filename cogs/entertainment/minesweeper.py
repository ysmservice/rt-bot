# Free RT - MineSweeper Game Extension

from discord.ext import commands
from discord import app_commands
import discord

from asyncio import TimeoutError
import re

from util.checks import alpha2num
from util import MineSweeper


class MSGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    @commands.hybrid_command(
        aliases=["ms", "MS", "マインスイーパー"],
        extras={
            "headding": {"ja": "マインスイーパー",
                         "en": "Minesweeper"},
            "parent": "Entertainment"
        }
    )
    @commands.cooldown(1, 15, commands.BucketType.user)
    @app_commands.describe(x="ゲームの横の長さ", y="ゲームの縦の長さ", bomb="ボムの数")
    async def minesweeper(self, ctx, x: int = 9, y: int = 9, bomb: int = 12):
        """!lang ja
        --------
        マインスイーパーというゲームで遊びます。

        Aliases
        -------
        ms, MS

        !lang en
        --------
        Play Minesweeper.

        Aliases
        -------
        ms, MS
        """
        game = MineSweeper(x, y, bomb)
        e = discord.Embed(
            title="縦の列を`ABC`, 横の行を`123`として送信してください",
            description=game.to_string(), color=self.bot.Colors.normal
        )
        msg = await ctx.send("マインスイーパー 1ターン目", embed=e)
        while True:
            try:
                msg = await self.bot.wait_for(
                    "message",
                    check=lambda m: (
                        m.author == ctx.author and
                        re.fullmatch(r"(\l+|\u+)\d+", m.content)
                    ),
                    timeout=60.0
                )
            except TimeoutError:
                return await msg.edit(content="タイムアウトしました。")
            await ctx.typing()
            result = game.open(
                alpha2num(re.match(r"(\l+|\u+)", msg.content).group()),
                int(re.search(r"\d+", msg.content).group())
            )[0]

            if result == 0:
                # 継続。
                await msg.edit(
                    content="マインスイーパー "
                            f"{int(msg.content.split()[1][:-4]) + 1}ターン目",
                    embed=discord.Embed(
                        title=msg.embeds[0].title,
                        description=game.to_string(),
                        color=self.bot.Colors.normal))
            elif result == 1:
                # クリア。
                return await msg.edit(
                    content=msg.content + "でクリア！",
                    embed=discord.Embed(
                        title="クリアしました、おめでとう！",
                        description=game.to_string("all"),
                        color=self.bot.Colors.normal))
            elif result == 2:
                # ゲームオーバー。
                return await msg.edit(
                    content=msg.content + "でゲームオーバー",
                    embed=discord.Embed(
                        title="ゲームオーバー...",
                        description=game.to_string("all"),
                        color=self.bot.Colors.unknown))


async def setup(bot):
    await bot.add_cog(MSGame(bot))
