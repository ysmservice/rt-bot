"""自動ドキュメンテーションヘルプ管理エクステンション  
コマンドフレームワークで定義したコマンドのコルーチン関数にあるドキュメンテーションから、ヘルプリストを自動で生成するためのエクステンションです。  
ヘルプメッセージの管理がとても楽になります。  
`bot.load_extension("rtlib.libs.dochelp")`で有効にすることができます。

Notes
-----
このエクステンションを読み込むのは他のエクステンションを読み込む前にしましょう。  
そうしないとこのエクステンションを読み込む前に読み込まれたコマンドのヘルプが登録されません。  
それと`rtlib.libs.on_command_add`のエクステンションが読み込まれていない場合は自動でこれが読み込まれます。

Examples
--------
@bot.command(name="そうだよ")
async def soudayo(ctx, mode="便乗"):
    \"\"\"
    !lang ja
    --------
    このコマンドはそうだよを作るコマンドです。

    Parameters
    ----------
    mode : str, default 便乗
        そうだよの後ろにくる括弧に入れるものです。
        デフォルトは便乗です。

    Examples
    --------
    そうだよを言わせます。
    `!そうだよ` -> そうだよ(便乗)
    \"\"\"
    await ctx.reply(f"そうだよ({mode})")

# 上のコマンドにあるドキュメンテーションがヘルプリストに自動で追加されます。"""

from typing import Callable, Tuple, List
from discord.ext import commands

from .util import DocParser


class DocHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data: dict = {}
        if "OnAddRemoveCommand" not in self.bot.cogs:
            self.bot.load_extension("rtlib.libs.on_command_add")

        self.dp = DocParser()
        self.dp.add_event(self.set_parent)
        self.indent_type = " "
        self.indent = 4

    @commands.Cog.listener()
    async def on_command_add(self, command):
        doc = command.callback.__doc__
        if doc:
            if command.cog is None:
                first_indent_count = 2
            else:
                first_indent_count = 1
            data = self.dp.parse(doc, furst_indent_count=first_indent_count,
                                 indent=self.indent, indent_type=self.indeent_type,
                                 session_id=)


def setup(bot):
    bot.add_cog(DocHelp(bot))
