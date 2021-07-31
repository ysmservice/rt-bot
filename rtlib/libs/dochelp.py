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


class DocHelp(commands.Cog):

    BLANKS = (" ", "\t", "　")
    HEADDINGS = {
        "Parameters": "# コマンドの引数",
        "Notes": "# メモ",
        "Warnings": "# 警告",
        "Examples": "# コマンドの使用例",
        "Raises": "# 起こり得るエラー",
        "Returns": "# 実行結果",
        "See Also": "# 関連事項"
    }
    TYPES = {
        "str": "文字列",
        "int": "整数",
        "float": "小数",
        "bool": "真偽値"
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

    def convert_normal(self, text: str, left: bool = True) -> Tuple[str, int]:
        # 文字列の最初にある空白を削除して改行を削除する。
        blank_count: int = 0
        if text and text[-1 if left else 0] not in self.BLANKS:
            while text[0 if left else -1] not in self.BLANKS:
                text = text[1:] if left else text[:-1]
                blank_count += 1
            if text[-1] == "\n":
                text = text[:-1]
        return text, blank_count

    def item_parser(self, now_item: str, text: str, blank_count: int, before: List[str, int, bool]) -> str:
        # 項目の中身をマークダウンに変換したりする。
        if now_item == "Parameters":
            # 引数の説明の項目だったら。
            if blank_count < before[1] or before[2]:
                # 引数名と型だったら。例：`arg : str`
                splited = text.split(":")
                result = f"**{splited[0]}** : {self.TYPES.get(splited[1], splited[1])}"
                # その他引数に付け加えているもの。

            else:
                # 引数の説明だったら。
                return text
        elif now_item

    def parse_doc(self, doc: str, item_parser: Optional[Callable] = None):
        item_parser = self.item_parser if item_parser is None else item_parser
        text, now_item, before, now = "", "", ["", 0, False], ""

        for line in doc.splitlines():
            (normal_text, blank_count), new = self.convert_normal(line), ""

            if all(char == "-" for char in self.remove_blanks(line)):
                # 項目名を置き換える。
                new = self.HEADDINGS.get(before[0], before[0]) + "\n"
                now_item = before[0]
                before[2] = True
            elif normal_text not in self.HEADDINGS:
                # 項目の中にあるものをitem_parserに通してできたものを追加する。
                new = item_parser(now_item, normal_text,
                                  blank_count, before) + "\n"
            else:
                before[2] = False

            text += new
            now += new
            before[:2] = noraml_text, blanik_count

    @commands.Cog.listener()
    async def on_command_add(self, command):
        command.callback.__doc__


def setup(bot):
    bot.add_cog(DocHelp(bot))
