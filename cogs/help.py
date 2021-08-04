# RT - Help

from sanic.response import json

from discord.ext import commands
import discord

from typing import List, Tuple


class Help(commands.Cog):

    CATEGORIES = {
        "bot": "RT",
        "server-tool": "ServerTool",
        "server-panel": "ServerPanel",
        "server-safety": "ServerSafety",
        "server-useful": "ServerUseful",
        "entertainment": "Entertainment",
        "individual": "Individual",
        "chplugin": "ChannelPlugin",
        "mybot": "MyBot",
        "other": "Other"
    }

    def __init__(self, bot):
        self.bot = bot
        self.help = self.bot.cogs["DocHelp"].data
        try:
            # Web Help APIのsetup
            self._setup_web()
        except Exception as e:
            print(e)

    def _setup_web(self):
        @self.bot.web.route("/help/<category>")
        async def help_category(request, category):
            category = self.CATEGORIES.get(category, category)
            count, lang = 0, "ja"
            data = {
                str(count := count + 1):[
                    key, self.help[category][key][lang][0]
                ]
                for key in self.help[category]
            } if category in self.help else {}
            data["status"] = "ok" if data else "Not found"
            data["title"] = category
            return json(data)

        @self.bot.web.route("/help/<category>/<command_name>")
        async def help_detail(request, category, command_name):
            category = self.CATEGORIES.get(category, category)
            data, lang = {"g-title": category, "status": "Not found"}, "ja"
            data["content"] = (f"# {command_name}\n"
                               + self.help[category][command_name]["ja"][1]
                                   .replace("### ", "## ")
                               if command_name in self.help.get(category, {})
                               else ".0.エラー：見つかりませんでした。")
            if not data["content"].startswith(".0.") and data["content"]:
                data["status"] = "ok"
            return json(data)

    @commands.command(
        extras={
            "headding": {
                "ja": "Helpが見れるウェブサイトのURLを表示します。",
                "en": "This command returns the URL of the web page."
            },
            "parent": "RT"
        }
    )
    async def help(self, ctx, *, word):
        """!lang ja
        --------
        ウェブサイトのURLを返します。  
        Discordからhelpを見たい場合は`dhelp`を実行してください。

        Parameters
        ----------
        word : str, optional
            この引数を指定するとこの引数に入れた言葉で検索をかけるウェブサイトのURLを返します。

        See Also
        --------
        dhelp
            Discord上でヘルプを閲覧します。

        !lang en
        --------
        This command returns the URL of the web page where you can see the RT help.  
        If you want help on Discord instead of the web, run `dhelp`.

        Parameters
        ----------
        word : str, optional
            Searches for help using the words in this argument.
 
        See Also
        --------
        dhelp
            See help on Discord."""
        embed = discord.Embed(
            title="Helpが必要ですか？",
            description="http://0.0.0.0" if self.bot.test else "https://rt-bot.com/help",
            color=self.bot.data["colors"]["normal"]
        )
        await ctx.reply(embed=embed)

    def _convert_embed(self, command_name: str, doc: str, **kwargs) -> List[discord.Embed]:
        # rtlib.libs.DocParserでドキュメンテーションからマークダウンに変換された文字列をEmbedに変換する関数。
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

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def test_help(self, ctx, category_name, command_name, lang="ja"):
        # ドキュメンテーションをマークダウンにしてEmbedにすることができているか確認するためのテスト用コマンド。
        embeds = self._convert_embed(
            command_name,
            self.help[category_name][command_name][lang][1]
        )
        for embed in embeds:
            await ctx.send(embed=embed)

    def search(self, word: str, lang: str) -> Tuple[str, str, List[Tuple[str, str]], List[Tuple[str, str]]]:
        # 指定された言葉で検索またはヘルプの取得を行う関数です。
        category, perfect, on_name, on_doc = "", "", [], []
        for category_name in self.help:
            if category_name == word:
                category = word
                break
            perfect = self.help[category_name].get(word, {lang: ["", ""]})[lang][1]
            if perfect == "":
                for cmd in self.help[category_name]:
                    if word in cmd:
                        on_name.append((category_name, cmd))
                    if word in self.help[category_name][cmd][lang][1]:
                        on_doc.append((category_name, cmd))
            else:
                break
        return category, perfect, on_name, on_doc

    @commands.command(aliases=["discord_help", "dh"],
                      extras={
                          "headding": {"ja": "DiscordからHelpを見ます。",
                                       "en": "Get help from Discord."},
                          "parent": "RT"
                      })
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def dhelp(self, ctx, *, word: str = None):
        """!lang ja
        --------
        Discordからヘルプを閲覧します。

        Parameters
        ----------
        word : コマンド名/検索ワード, optional
            表示したいヘルプのコマンド名です。  
            コマンド名ではない言葉が指定された場合は検索します。

        Aliases
        -------
        `discord_help`, `dh`

        !lang en
        --------
        上の英語バージョンをここに。"""
        replace_language = True
        lang = self.bot.cogs["Language"].get(ctx.author.id)

        if word is None:
            # もしカテゴリー一覧を表示すればいいだけなら。
            embeds = [
                discord.Embed(
                    title="Help - カテゴリー一覧",
                    description="`" + "`\n`".join(self.help) + "`",
                    color=self.bot.colors["normal"]
                )
            ]
        else:
            # 検索/コマンド/カテゴリー探しを行う。
            await ctx.trigger_typing()
            category, perfect, on_name, on_doc = self.search(word, lang)

            if category:
                # もしカテゴリー名が一致したなら。
                embeds = [
                    discord.Embed(
                        title="Help - " + category,
                        description="\n".join(f"`{n}` {(k := self.help[category][n]).get(lang, k['ja'])[0]}"
                                              for n in self.help[category]),
                        color=self.bot.colors["normal"]
                    )
                ]
            elif perfect:
                # もしコマンド名が一致したなら。
                embeds = self._convert_embed(
                    word, perfect,
                    color=self.bot.colors["normal"]
                )
                replace_language = False
            else:
                # もし何も一致しないなら検索結果を表示する。
                embeds = [
                    discord.Embed(
                        title="検索結果", color=self.bot.colors["normal"]
                    )
                ]
                for name_, value in (("名前部分一致", on_name), ("説明部分一致", on_doc)):
                    embeds[0].add_field(
                        name=name_, value=("\n".join(
                                                f"`{n}` {self.help[category][n][lang][0]}"
                                                for category, n in value)
                                           if value else "見つかりませんでした。")
                    )
        for embed in embeds:
            embed.set_footer(
                text="`rt!dhelp <名前>`を実行することで詳細を見ることができます。")
            await ctx.send(content=ctx.author.mention, embed=embed,
                           replace_language=replace_language)


def setup(bot):
    bot.add_cog(Help(bot))
