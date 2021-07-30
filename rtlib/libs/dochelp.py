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

from discord.ext import commands


class DocHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data: dict = {}
        if "OnAddRemoveCommand" not in self.bot.cogs:
            self.bot.load_extension("rtlib.libs.on_command_add")

    @commands.Cog.listener()
    async def on_command_add(self, command):
        command.callback.__doc__


def setup(bot):
    bot.add_cog(DocHelp(bot))
