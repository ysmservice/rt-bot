"""自動ドキュメンテーションヘルプ管理エクステンション  
コマンドフレームワークで定義したコマンドのコルーチン関数にあるドキュメンテーションから、ヘルプリストを自動で生成するためのエクステンションです。  
ヘルプメッセージの管理がとても楽になります。  
`bot.load_extension("rtlib.libs.dochelp")`で有効にすることができます。  
### 書き込み方法
下のExamplesのようにすれば良いです。  
ですがもし親コマンドのいないコマンドのヘルプの場合は以下のようにカテゴリーを指定してください。
```
!parent カテゴリー名
-------
```
これで自動でカテゴリーが作成されそのカテゴリーにそのコマンドのヘルプが書き込まれます。  
親コマンドのいないコマンドとはグループコマンドやpingコマンドなどの他と関連するコマンドのないコマンドのことです。
### 出力されたヘルプ
`bot.cogs["DocHelp"].data`から参照することができます。  
日本語で開く例：`bot.cogs["DocHelp"].data["カテゴリーX"]["えっくすふぁいる"]["ja"]`  
言語については下のNotesをみてください。

Notes
-----
### 読み込みについて
このエクステンションを読み込むのは他のエクステンションを読み込む前にしましょう。  
そうしないとこのエクステンションを読み込む前に読み込まれたコマンドのヘルプが登録されません。  
それと`rtlib.libs.on_command_add`のエクステンションが読み込まれていない場合は自動でこれが読み込まれます。
### ヘルプの言語について
ヘルプの言語は複数設定することができます。  
下のExamplesにもありますが`!lang ja`のように設定をすることができます。  
書き方は`!lang 言語名`です。  
デフォルトは`ja`でこれを書かない場合は`ja`となります。
### インデントについて
インデントはデフォルトでは空白四つでなければ対応していません。  
ですがこの設定は以下のように変更することができます。  
インデントの数の設定：`bot.cogs["DocHelp"].indent: int` (デフォルトが`4`)  
インデントの文字設定：`bot.cogs["DocHelp"].indent_type: str` (デフォルトが`" "`)
### 項目の交換に使う文字列について
`Parameters`などの項目名の交換に使う文字列は変更することが可能です。  
`bot.cogs["DocHelp"].dp`にドキュメンテーションをマークダウンに変換するためのクラスのインスタンスがあります。  
そのインスタンスに`HEADDINGS`と言う属性があります。  
ここに辞書形式で項目名の交換に使う文字列があります。  
これを自分の好きなやつと交換しましょう。

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

from typing import Callable, Tuple, List, Literal
from discord.ext import commands

from aiofiles import open as async_open
from ujson import loads, dumps

from .util import DocParser


class DocHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data: dict = {}
        if "OnAddRemoveCommand" not in self.bot.cogs:
            self.bot.load_extension("rtlib.libs.on_command_add")

        self.dp = DocParser()
        self.dp.add_event(self._set_parent, "parent")
        self.indent_type = " "
        self.indent = 4
        self.data = {"other": {}}

    @commands.Cog.listener()
    async def on_command_add(self, command):
        doc = command.callback.__doc__
        if doc:
            # 親コマンドがいるかいないかなどを判定する。
            # もし親コマンドがいないのならセッションIDにコマンド名を入れる。
            session_id = 0
            if (isinstance(command, commands.Group)
                    or isinstance(command, commands.Command)):
                if not command.parents:
                    session_id = command.name

            # ドキュメンテーションをマークダウンにする。
            first_indent_count = 2 if command.cog else 1
            data = self.dp.parse(doc, first_indent_count=first_indent_count,
                                 indent=self.indent, indent_type=self.indent_type,
                                 session_id=session_id)

            wrote, doc = False, {}
            if isinstance(session_id, int):
                # 親コマンドがいるコマンドのヘルプを親コマンドに追記する。
                for lang in data:
                    doc[lang] = f"\n## {command.name}\n" + data[lang]
                cmd_parent = ("I wanna be the guy!" if command.parent.name is None
                              else command.parent.name)
                # 親コマンドのヘルプを探します。親コマンドのヘルプは下のelseで登録されます。
                for category_name in self.data:
                    if cmd_parent in self.data[category_name]:
                        for lang in self.data[category_name][command.parent.name]:
                            if lang in data:
                                # 親コマンドのヘルプにコマンドのヘルプを追記する。
                                self.data[category_name][command.parent.name][lang] += doc[lang]
                                wrote = True
                        break
                # もしカテゴリーが見つからないのならotherカテゴリーにする。
                if not wrote:
                    n = (command.name if command.parent.name == "I wanna be the guy!"
                         else command.parent.name)
                    for lang in doc:
                        self.data["other"][n] = "\n" + doc[lang][2:]
            else:
                # 親コマンドがいないコマンドの場合コマンドのヘルプを新しく書き込む。
                # もしコマンドのヘルプに`!parent`があるならself._set_parentが呼ばれます。
                # `!parent`は親コマンドがいないコマンドに置きます。
                # そして`self._set_parent`が呼ばれそこでカテゴリーが登録されます。
                # そのカテゴリーに親コマンドがいないコマンドのヘルプを書き込みます。
                # 例：`!parent 安全`
                for category_name in self.data:
                    if session_id in self.data[category_name]:
                        self.data[category_name][session_id] = data
                        wrote = True
                        break
                # もしカテゴリーが割り振られなかった場合はotherカテゴリーを作りそこに入れる。
                if not wrote:
                    self.data["other"][session_id] = data

    @commands.Cog.listener()
    async def on_command_remove(self, command):
        # もしコマンドが削除されたならそのコマンドのヘルプも削除する。
        # コマンドがグループコマンドではない場合は何もしない。
        if command:
            for category_name in self.data:
                if command.name in self.data[category_name]:
                    del self.data[category_name]
                    break

    def _set_parent(self, line: str, now: dict, before: dict) -> Literal[None, False]:
        # コマンドのドキュメンテーションでもし!parentがある際に呼び出される関数です。
        if isinstance(now["session_id"], str):
            # もし親コマンドがいないならカテゴリー名を取り出してヘルプリストに追加する。
            category_name = before["line"].replace("!parent ", "")
            if category_name not in self.data:
                self.data[category_name] = {}
            self.data[category_name][now["session_id"]] = ""
            return False

    async def output(self, path: str) -> None:
        """作ったヘルプのデータをjson形式でファイルに出力します。
        
        Parameters
        ----------
        path : str
            出力するファイルのパスです。"""
        async with async_open(path, "w") as f:
            await f.write(dumps(self.data))

    async def input(self, path: str) -> None:
        """rtlib.libs.dochelpが読み込める形式のjsonファイルのヘルプを読み込みます。
        
        Parameters
        ----------
        path : str
            読みこむファイルのパスです。"""
        async with async_open(path, "r") as f:
            self.data.update(loads(await f.read()))

    def add_help(self, category: str, help_name: str, lang: str, content: str) -> None:
        """ヘルプを追加します。

        Parameters
        ----------
        category : str
            追加するヘルプのカテゴリーです。
        help_name : str
            追加するヘルプの名前です。  
            大抵コマンド名を入れます。
        lang : str
            言語名です。  
            もし日本語なら`ja`を入れましょう。
        content : str
            ヘルプの内容です。"""
        if category not in self.data:
            self.data[category] = {}
        if help_name not in self.data[category]:
            self.data[category][help_name] = {}
        self.data[category][help_name][lang] = content

    def remove_category(self, category: str) -> None:
        """ヘルプリストのカテゴリーを削除します。

        Parameters
        ----------
        category : str
            削除するカテゴリーです。

        Raises
        ------
        KeyError : カテゴリーが見つからない場合発生します。"""
        del self.data[category]

    def remove_help(self, category: str, help_name: str) -> None:
        """ヘルプリストからヘルプを削除します。

        Parameters
        ----------
        category : str
            削除するヘルプがあるカテゴリーの名前です。
        help_name : str
            削除するヘルプの名前です。

        Raises
        ------
        KeyError : 指定されたカテゴリーまたはヘルプが存在しない際に発生します。"""
        del self.data[category][help_name]


def setup(bot):
    bot.add_cog(DocHelp(bot))
