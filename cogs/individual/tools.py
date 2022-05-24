# Free RT - Tools For Dashboard


from discord.ext import commands
from discord import app_commands

from asyncio import wait_for, TimeoutError
from time import sleep
import operator
import ast

from util.settings import Context
from util import RT



_OP_MAP = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Mult: operator.mul,
    ast.Invert: operator.neg,
    ast.Pow: operator.pow,
}


def custom_eval(node_or_string):
    node_or_string = ast.parse(node_or_string.lstrip(" \t"), mode='eval')
    if isinstance(node_or_string, ast.Expression):
        node_or_string = node_or_string.body
    def _convert(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp) and isinstance(node.op, tuple(_OP_MAP.keys())):
            sleep(0.1)  # タイムアウト実装のため。
            left = _convert(node.left)
            right = _convert(node.right)
            if (right > 5 or left > 10000) and isinstance(node.op, ast.Pow):
                raise TimeoutError("Powor too big.")
            return _OP_MAP[type(node.op)](left, right)
        else:
            raise ValueError("can't calculate node of type '%s'" % node.__class__.__name__)
    return _convert(node_or_string)


class Tools(commands.Cog):
    def __init__(self, bot: RT):
        self.bot = bot

    @commands.hybrid_command(
        extras={
            "headding": {
                "ja": "式を入力して計算を行うことができます。", "en": "Calculation by expression"
            }, "parent": "Individual"
        }
    )
    @app_commands.describe(expression="計算する式")
    async def calc(self, ctx: Context, *, expression: str):
        """!lang ja
        --------
        渡された式から計算をします。

        Parameters
        ----------
        expression : str
            式です。

        !lang en
        --------
        Calculate from the expression given.

        Parameters
        ----------
        expression : str
            Expression"""
        try:
            x = await wait_for(
                self.bot.loop.run_in_executor(None, custom_eval, expression), 3
            )
        except (SyntaxError, ValueError):
            await ctx.send("計算式がおかしいです！")
        except ZeroDivisionError:
            await ctx.send("0で割り算することはできません!")
        except TimeoutError:
            await ctx.send("計算範囲が大きすぎます！頭壊れます。")
        else:
            await ctx.reply(f"計算結果：`{x}`")

    @commands.command(
        extras={
            "headding": {
                "ja": "文字列を逆順にします。", "en": "Reverse text"
            }
        }
    )
    async def reverse(self, ctx: Context, *, bigbox):
        await ctx.reply(f"結果：\n```\n{bigbox[::-1]}\n```")

    @commands.command(
        extras={
            "headding": {
                "ja": "文字列の交換を行います。", "en": "Replace text"
            }
        }
    )
    async def replace(self, ctx: Context, before, after, *, text):
        await ctx.reply(f"結果：{text.replace(before, after)}")

    @commands.command(
        "RTを追い出します。", extras={
            "headding": {
                "ja": "Free RTをサーバーから追い出します。", "en": "Kick RT"
            }
        }
    )
    @commands.has_guild_permissions(administrator=True)
    async def leave(self, ctx: Context, password="ここに「うらみのワルツ」と入力してください。"):
        if password == "うらみのワルツ":
            await ctx.guild.leave()
            await ctx.reply("* 返事がない。ただの屍のようだ。")
        else:
            await ctx.reply("「うらみのワルツ」を入力しなければ抜けません。")


async def setup(bot):
    await bot.add_cog(Tools(bot))
