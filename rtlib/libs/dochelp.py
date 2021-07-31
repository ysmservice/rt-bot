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
from typing import Callable


class DocHelp(commands.Cog):

    BLANKS = (" ", "\t", "　")
    HEADDINGS = {
        "Parameters": "# コマンドの引数",
        "Examples": "# コマンドの使用例"
    }

    def __init__(self, bot):
        self.bot = bot
        self.data: dict = {}
        if "OnAddRemoveCommand" not in self.bot.cogs:
            self.bot.load_extension("rtlib.libs.on_command_add")

    def remove_blanks(self, text: str, remove_new_line: bool = True) -> str:
        # 空白を削除する。
        for blank in self.BLANKS:
            text = text.replace(blank, "")
        if remove_new_line:
            text = text.replace("\n", "")
        return text

    def convert_normal(self, text: str) -> str:
        # 文字列の最初にある空白を削除して改行を削除する。
        if text and text[-1] not in self.BLANKS:
            while text[0] not in self.BLANKS:
                text = text[1:]
            if text[-1] == "\n":
                text = text[:-1]
        return text

    def item_parser(self, now_item: str, text: str):
        if now_item == "Parameters":
            if now_item

    def parse_doc(self, doc: str, item_parser: Optional[Callable] = None):
        item_parser = self.item_parser if item_parser is None else item_parser
        text, now_item, before, now = "", "", "", ""

        for line in doc.splitlines():
            normal_text, new = self.convert_normal(line), ""

            if all(char == "-" for char in self.remove_blanks(line)):
                # 項目名
                new = self.HEADDINGS.get(before, before) + "\n"
                now_item = before
            elif normal_text not in self.HEADDINGS:
                # 項目の中にあるものをitem_parserに通してできたものを追加する。
                new = item_parser(normal_text) + "\n"

            text += new
            now += new
            before = noraml_text

    @commands.Cog.listener()
    async def on_command_add(self, command):
        command.callback.__doc__


def setup(bot):
    bot.add_cog(DocHelp(bot))
