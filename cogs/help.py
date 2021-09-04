# RT - Help

from discord.ext import commands
import discord

from rtlib.ext import componesy, Embeds
from rtlib import OAuth, slash

from sanic.response import json
from typing import List, Tuple
from data import get_headers


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

    @commands.Cog.route("/help/<category>/<command_name>")
    @OAuth.login_want()
    async def help_detail(self, request, category, command_name):
        self.help = self.bot.cogs["DocHelp"].data
        category = self.CATEGORIES.get(category, category)
        lang = (self.bot.cogs["Language"].get(request.ctx.user.id)
                if request.ctx.user else "ja")
        if command_name:
            data = {"g-title": category, "status": "Not found"}
            data["content"] = (f"# {command_name}\n"
                            + self.help[category][command_name][lang][1]
                                .replace("### ", "## ")
                            if command_name in self.help.get(category, {})
                            else ".0.エラー：見つかりませんでした。")
            if not data["content"].startswith(".0.") and data["content"]:
                data["status"] = "ok"
        else:
            count = 0
            data = {
                str(count := count + 1):[
                    key, self.help[category][key][lang][0]
                ]
                for key in self.help[category]
            } if category in self.help else {}
            data["status"] = "ok" if data else "Not found"
            data["title"] = category
        return json(data, headers=get_headers(self.bot, request))

    def search(self, word: str, lang: str) -> Tuple[str, str, List[Tuple[str, str]], List[Tuple[str, str]]]:
        # 指定された言葉で検索またはヘルプの取得を行う関数です。
        c, category, perfect, on_name, on_doc = False, "", "", [], []
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
                c = category_name
                break
        return c, category, perfect, on_name, on_doc

    async def on_select(self, select, interaction):
        # カテゴリー選択がされたら。
        ctx = await self.bot.get_context(interaction.message)
        if interaction.message.content:
            user = interaction.message.guild.get_member(
                int(interaction.message.content
                    .replace("<@", "").replace(">", "").replace("!", ""))
            )
        elif interaction.message.reference.cached_message:
            user = interaction.message.reference.cached_message.author
        else:
            return await interaction.response.send_message(
                "メッセージが古すぎるため操作を行うことができませんでした。")
        if (select.values and select.values[0] != "None" and user
                and user.id == interaction.user.id):
            # 選択されたものを引数としてdhelpのコマンドを実行する。
            await self.dhelp(ctx, word=select.values[0],
                             interaction=interaction)

    def get_view_args(self, lang, category):
        # 作るViewのデータを取得するための関数です。
        if category is None:
            options = [discord.SelectOption(label="...", value="None")]
            placeholder = "..."
        else:
            options = [discord.SelectOption(
                           label=cmd, value=cmd,
                           description=self.help[category][cmd][lang][0]
                       ) for cmd in self.help[category]]
            placeholder = "コマンド選択"
        return [
            ("Select", self.on_select, {
                "options": [discord.SelectOption(
                               label=self.CATEGORY_JA.get(category, category),
                               value=category
                           ) for category in self.help],
                "placeholder": "カテゴリー選択"
            }),
            ("Select", self.on_select, {
                "options": options, "placeholder": placeholder
            })
        ]

    def make_view(self, user, lang, category=None):
        # Viewを作るための関数です。
        view = componesy.View("HelpView", timeout=60)
        for _, func, kwargs in self.get_view_args(lang, category):
            view.add_item("Select", func, **kwargs)
        return view

    @commands.command(
        name="help",
        aliases=["h", "Help_me,_ERINNNNNN!!", "たすけて！"],
        extras={
              "headding": {"ja": "Helpを表示します。",
                           "en": "Get help."},
              "parent": "RT"
        }
    )
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def dhelp(self, ctx, *, word: str = None, interaction=None):
        """!lang ja
        --------
        コマンドの使い方が載っているヘルプを表示します。

        Parameters
        ----------
        word : コマンド名/検索ワード, optional
            表示したいヘルプのコマンド名です。  
            コマンド名ではない言葉が指定された場合は検索します。

        Aliases
        -------
        `h`, `たすけて！`, `Help_me,_ERINNNNNN!!`

        !lang en
        --------
        Displays a help page with information on how to use the command.

        Parameters
        ----------
        word : command name/search word, optional
            The command name of the help to be displayed.  
            If a word that is not a command name is specified, a search will be performed."""
        self.help = self.bot.cogs["DocHelp"].data
        lang = self.bot.cogs["Language"].get(ctx.author.id)
        edit = ctx.message.author.id == self.bot.user.id
        reply = True

        if word is None:
            # もしカテゴリー一覧を表示すればいいだけなら。
            embed = discord.Embed(
                title="Help - カテゴリー選択",
                description=(
                    "カテゴリーを選択するとそのカテゴリーにあるコマンドが表示されます。\nまたこちらからも見れます："
                    "http://0.0.0.0" if self.bot.test else "https://rt-bot.com/help.html"
                ),
                color=self.bot.colors["normal"]
            )
            view = self.make_view(
                getattr(interaction, "user", None) or ctx.author, lang
            )
            await ctx.reply(embed=embed, view=view)
        else:
            c, category, perfect, on_name, on_doc = self.search(word, lang)

            if category:
                # もしカテゴリー名が一致したなら。
                description = "\n".join(
                    f"`{cmd}` {self.help[category][cmd][lang][0]}"
                    for cmd in self.help[category]
                )
                embed = discord.Embed(
                    title=f"Help - {word}",
                    description=description,
                    color=self.bot.colors["normal"]
                )
                view = self.make_view(
                    getattr(interaction, "user", None) or ctx.author,
                    lang, category
                )
                kwargs = {"embed": embed, "view": view}
            elif perfect:
                # もしコマンド名が一致したなら。
                user = getattr(interaction, "user", None) or ctx.author
                embeds = Embeds(
                    "HelpCommandDetails", target=user.id,
                    embeds=self.bot.cogs["DocHelp"].convert_embed(
                        word, perfect,
                        color=self.bot.colors["normal"]
                    )
                )
                edit, reply = False, not bool(interaction)
                if not reply:
                    await ctx.message.delete()
                if len(embeds.embeds) == 1:
                    kwargs = {"embed": embeds.embeds[0], "view": self.make_view(user, lang, c),
                              "target": user.id}
                    del embeds
                else:
                    embeds.items = embeds.items + self.get_view_args(lang, c)
                    kwargs = {"embeds": embeds, "target": user.id}
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
                kwargs = {"embed": embed}

            if edit:
                kwargs["target"] = ctx.author.id
                await ctx.message.edit(**kwargs)
            elif reply:
                await ctx.reply(**kwargs)
            else:
                await ctx.send(interaction.user.mention, **kwargs)


def setup(bot):
    bot.add_cog(Help(bot))
