"""自動ドキュメンテーションヘルプ管理エクステンション  
コマンドフレームワークで定義したコマンドのコルーチン関数にあるドキュメンテーションから、ヘルプリストを自動で生成するためのエクステンションです。  
ヘルプメッセージの管理がとても楽になります。  
`bot.load_extension("rtlib.ext.dochelp")`で有効化することができます。  
また`rtlib.setup`でも有効化できます。  
これを読み込む場合は`on_command_add`が自動で読み込まれるのでこれを読み込まないでください。
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
それと`rtlib.ext.on_command_add`のエクステンションが読み込まれていない場合は自動でこれが読み込まれます。
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
import discord

from aiofiles import open as async_open
from ujson import loads, dumps

from .util import DocParser


class DocHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data: dict = {}
        if "OnCommandAdd" not in self.bot.cogs:
            self.bot.load_extension("rtlib.ext.on_command_add")

        self.dp = DocParser()
        self.dp.add_event(self._set_parent, "parent")
        self.indent_type = " "
        self.indent = 4
        self._prefix = None

    def convert_embed(self, command_name: str, doc: str, **kwargs) -> List[discord.Embed]:
        """渡されたコマンド名とヘルプ(マークダウン)をEmbedにします。

        Parameters
        ----------
        command_name : str
            コマンド名です。
        doc : str
            内容です。
        **kwargs : dict
            Embedに渡すキーワード引数です。

        Returns
        -------
        List[discord.Embed]"""
        now, text, embed, embeds, field_length = ["description", 0], "", None, [], 0
        onecmd = "## " not in doc
        make_embed = lambda text: discord.Embed(
            title=f"**{command_name}**", description=text, **kwargs)

        for line in (docs := doc.splitlines()):
            is_item = line.startswith("## ")
            # Embedやフィールドを作るか作るないか。
            if is_item:
                if now[0] == "description":
                    embed = make_embed(text[:-1])
                now = ["field", len(embed.fields)]
            if now[0] == "field":
                if field_length == 25:
                    embeds.append(embed)
                    embed, now = None, ["description", 0]
                else:
                    embed.add_field(
                        name=f"‌\n**{line[3:]}**", value="", inline=False)
                    now[0] = "field_name"
            # 文字列を整える。
            if line.startswith("### "):
                line = "**#** " + line[4:]
            if line.endswith("  "):
                line = line[:-2]
            if line.count("*") > 3 and line[2] != "#":
                line = line.replace("**", "*`", 1).replace("**", "`", 1) + "*"
            # フィールドのテキストにlineを追加する。
            if now[0] == "field_name" and not is_item:
                embed.set_field_at(
                    now[1], name=embed.fields[now[1]].name,
                    value=embed.fields[now[1]].value + line + "\n",
                    inline=False
                )
            # Embedのdescriptionに追加予定の変数にlineを追記する。
            if embed is None:
                text += f"{line}\n"

        # fieldが一つでもないとEmbedが作られない、そのためEmbedが空の場合作る。
        if embed is None:
            embed = make_embed(text[:-1])
        # Embed一つに25個までフィールドが追加可能で25に達しないと上では結果リストにEmbedを追加しない。
        # だからEmbedを追加しておく。
        if field_length < 25 and embed is not None:
            embeds.append(embed)
        return embeds

    @property
    def prefix(self):
        if self._prefix is None:
            self._prefix = self.bot.command_prefix
            if isinstance(self._prefix, (tuple, list)):
                self._prefix = self._prefix[0]
        return self._prefix

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
                    doc[lang] = (f"\n## {self.prefix}{command.qualified_name}\n"
                                 + data[lang])
                cmd_parent = ("I wanna be the guy!" if command.parent.name is None
                              else command.parent.name)
                # 親コマンドのヘルプを探します。親コマンドのヘルプは下のelseで登録されます。
                for category_name in self.data:
                    if cmd_parent in self.data[category_name]:
                        for lang in self.data[category_name][command.parent.name]:
                            if lang in data:
                                # 親コマンドのヘルプにコマンドのヘルプを追記する。
                                self.data[category_name][command.parent.name][lang][1] += doc[lang]
                                wrote = True
                        break
                # もしカテゴリーが見つからないのならOtherカテゴリーにする。
                if not wrote:
                    n = (command.name if command.parent.name == "I wanna be the guy!"
                         else command.parent.name)
                    for lang in doc:
                        self.data["Other"][n][lang][1] = "\n" + doc[lang][2:]
            else:
                # 親コマンドがいないコマンドの場合コマンドのヘルプを新しく書き込む。
                # もしコマンドのヘルプに`!parent`があるならself._set_parentが呼ばれます。
                # `!parent`は親コマンドがいないコマンドに置きます。
                # そして`self._set_parent`が呼ばれそこでカテゴリーが登録されます。
                # そのカテゴリーに親コマンドがいないコマンドのヘルプを書き込みます。
                # 例：`!parent 安全`
                for lang in data:
                    headdings = command.extras.get("headding", {})
                    data[lang] = [headdings.get(lang, ""), data[lang]]
                for category_name in self.data:
                    if session_id in self.data[category_name]:
                        self.data[category_name][session_id] = data
                        wrote = True
                        break
                # もしカテゴリーが割り振られなかった場合はotherカテゴリーを作りそこに入れる。
                # この際commands.command(extras=ここ)のここでparentを指定されたらそこからカテゴリーをとる。
                if not wrote:
                    parent = "Other" if (parent := command.extras.get("parent")) is None else parent
                    if parent not in self.data:
                        self.data[parent] = {}
                    self.data[parent][session_id] = data

    @commands.Cog.listener()
    async def on_command_remove(self, command):
        # もしコマンドが削除されたならそのコマンドのヘルプも削除する。
        # コマンドがグループコマンドではない場合は何もしない。
        if command:
            for category_name in self.data:
                if command.name in self.data[category_name]:
                    del self.data[category_name][command.name]
                    break

    def _set_parent(self, line: str, now: dict, before: dict) -> Literal[None, False]:
        # コマンドのドキュメンテーションでもし!parentがある際に呼び出される関数です。
        if isinstance(now["session_id"], str):
            # もし親コマンドがいないならカテゴリー名を取り出してヘルプリストに追加する。
            category_name = before["line"].replace("!parent ", "")
            if category_name not in self.data:
                self.data[category_name] = {}
            self.data[category_name][now["session_id"]] = {}
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
