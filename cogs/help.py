# RT - Help

from discord.ext import commands
import discord

from rtlib.ext import componesy, Embeds
from sanic.response import json
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
    CATEGORY_JA = {
        "ServerTool": "サーバーツール",
        "ServerPanel": "サーバーパネル",
        "ServerSafety": "サーバー安全",
        "ServerUseful": "サーバー便利",
        "Entertainment": "娯楽",
        "Individual": "個人",
        "ChannelPlugin": "チャンネルプラグイン",
        "MyBot": "MyBot",
        "Other": "その他"
    }

    def __init__(self, bot):
        self.bot = bot
        self.help = self.bot.cogs["DocHelp"].data

    @commands.Cog.route("/help/<category>")
    async def help_category(self, request, category):
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

    @commands.Cog.route("/help/<category>/<command_name>")
    async def help_detail(self, request, category, command_name):
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

    def get_cmds(self, category, lang="ja"):
        for cmd in category:
            yield cmd, category[cmd].get(lang, category[cmd]["ja"])[0]

    async def on_command_select(self, view, select, interaction):
        await self.on_category_select(view, select, interaction)

    async def on_category_select(self, view, select, interaction):
        lang = self.bot.cogs["Language"].get(interaction.user.id)
        if select.values:
            ctx = await self.bot.get_context(interaction.message)
            ctx.author = interaction.user
            await self.dhelp(ctx, select.values[0])

    @commands.command(aliases=["discord_help", "dh"],
                      extras={
                          "headding": {"ja": "DiscordからHelpを見ます。",
                                       "en": "Get help from Discord."},
                          "parent": "RT"
                      })
    @commands.cooldown(1, 5, commands.BucketType.user)
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
        lang = self.bot.cogs["Language"].get(ctx.author.id)

        if word is None:
            # もしカテゴリー一覧を表示すればいいだけなら。
            embed = discord.Embed(
                title="Help - カテゴリー選択",
                description="カテゴリーを選択するとそのカテゴリーにあるコマンドが表示されます。",
                color=self.bot.colors["normal"]
            )
            view = componesy.View("HelpCategorySelector", timeout=30)
            view.add_item(
                "Select",
                options=[discord.SelectOption(
                            label=self.CATEGORY_JA.get(category, category)
                                  if lang == "ja" else category,
                            value=category
                         ) for category in self.help]
            )
            await ctx.reply(embed=embed, view=view)
        else:
            await ctx.trigger_typing()
            category, perfect, on_name, on_doc = self.search(word, lang)

            if category:
                # もしカテゴリー名が一致したなら。
                description, view = "", componesy.View("HelpCategoryCommands")
                options = []
                for cmd, headding in self.get_cmds(word, lang):
                    description += f"`{cmd}` {headding}\n"
                    options.append(discord.SelectOption(label=cmd, value=cmd))
                embed = discord.Embed(
                    title=f"Help - {word}",
                    description=description,
                    color=self.bot.colors["normal"]
                )
                view.add_item("Select", options=options)
                kwargs = {"embed": embed, "view": view}
            elif perfect:
                # もしコマンド名が一致したなら。
                embeds = Embeds(
                    "HelpCommandDetails", target=ctx.author.id,
                    embeds=self._convert_embed(
                        word, perfect,
                        color=self.bot.colors["normal"]
                    )
                )
                kwargs = {"embeds": embeds}
            else:
                # もし何も一致しないなら検索結果を表示する。
                embed = discord.Embed(
                    title="検索結果", color=self.bot.colors["normal"]
                )
                for name, value in (("名前部分一致", on_name), ("説明部分一致", on_doc)):
                    embed.add_field(
                        name=name,
                        value=("\n".join(
                            f"`{n}` {self.help[category][n][lang][0]}"
                            for category, n in value
                            ) if value else "見つかりませんでした。")
                    )
                kwargs = {"embed": embed, "view": view}

            if ctx.message.author.id == self.bot.user.id:
                kwargs["target"] = ctx.author.id
                await ctx.message.send(ctx.author.mention, **kwargs)
            else:
                await ctx.reply(**kwargs)


def setup(bot):
    bot.add_cog(Help(bot))
