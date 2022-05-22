# Free RT - Help

from typing import Tuple, List, Union

from discord.ext import commands, tasks
import discord

from util.page import EmbedPage
from util import RT, TimeoutView


def convert_commands(data, word=None) -> Union[dict, str]:
    "カテゴリーをなくしてcommandsだけリストにして返す。wordが指定されればそのコマンドのカテゴリを返す。"
    if word is None:
        commands = {}
        for category in data:
            commands.update(data[category])
        return commands
    else:
        for category in data:
            if word in data[category]:
                return category


def get_command_help(client, commands, cmd_name, lang):
    return EmbedPage(
        data=client.cogs["DocHelp"].convert_embed(
            cmd_name, commands[cmd_name][lang][1], color=client.colors["normal"]
        )
    ).data[0]


def get_category_help(client, data, category_name, lang):
    description = "\n".join(
        f"`{cmd}` {data[category_name][cmd][lang][0]}"
        for cmd in data[category_name]
        if len(data[category_name][cmd][lang]) >= 2
    )
    return discord.Embed(
        title=f"Help - {category_name}",
        description=description,
        color=client.colors["normal"]
    )


class HelpCategorySelect(discord.ui.Select):

    CATEGORIES = {
        "bot": "RT",
        "server-tool": "ServerTool",
        "server-panel": "ServerPanel",
        "server-safety": "ServerSafety",
        "server-useful": "ServerUseful",
        "entertainment": "Entertainment",
        "individual": "Individual",
        "chplugin": "ChannelPlugin",
        "music": "Music",
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
        "Music": "音楽",
        "Other": "その他"
    }

    def __init__(self, user_id, lang, data: dict):
        super().__init__(
            placeholder="カテゴリー選択" if lang == "ja" else "Category",
            min_values=1, max_values=1, custom_id=str(user_id),
            options=[discord.SelectOption(label=self.get_category_name(c, lang), value=c) for c in data]
        )

    def get_category_name(self, category, lang):
        c = self.CATEGORIES.get(category, category)
        if lang == "ja":
            c = self.CATEGORY_JA.get(c, c)
        return c

    async def callback(self, interaction: discord.Interaction):
        help = interaction.client.cogs["DocHelp"].data
        lang = interaction.client.cogs["Language"].get(interaction.user.id)
        if interaction.user.id != int(self.custom_id):
            return await interaction.response.send_message(
                "あなたはこのhelpを操作することはできません。" if lang == "ja" else "You can't control this help.", ephemeral=True
            )

        category = self.values[0]
        embed = get_category_help(interaction.client, help, category, lang)
        view = HelpView(interaction.user.id, lang, help, category)
        await interaction.response.edit_message(
            embed=embed, view=view
        )


class HelpCommandSelect(discord.ui.Select):
    def __init__(self, user_id, lang, data: dict, category: str):
        super().__init__(
            placeholder="コマンド選択" if lang == "ja" else "Command",
            min_values=1, max_values=1, custom_id=str(user_id) + "_2",
            options=[discord.SelectOption(
                label=c, value=c, description=data[category][c][lang][0]
            ) for c in data[category]]
        )

    async def callback(self, interaction: discord.Interaction):
        help = interaction.client.cogs["DocHelp"].data
        lang = interaction.client.cogs["Language"].get(interaction.user.id)
        if interaction.user.id != int(self.custom_id[:-2]):
            return await interaction.response.send_message(
                "あなたはこのhelpを操作できません。" if lang == "ja" else "You can't control this help.", ephemeral=True
            )

        commands = convert_commands(help)
        embed = get_command_help(interaction.client, commands, self.values[0], lang)
        await interaction.response.edit_message(
            embed=embed
        )


class HelpView(TimeoutView):
    def __init__(self, user_id, lang, data, category=None):
        super().__init__()
        self.add_item(HelpCategorySelect(user_id, lang, data))
        if category:
            self.add_item(HelpCommandSelect(user_id, lang, data, category))


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
        "music": "Music",
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
        "Music": "音楽",
        "Other": "その他"
    }

    def __init__(self, bot: RT):
        self.bot = bot
        self.update_help.start()
        self.bot.backend = False

    async def update_help_web(self):
        "ウェブのヘルプを更新します。"
        async with self.bot.session.post(
            f"{self.bot.get_url()}/api/help/update",
            json=self.bot.cogs["DocHelp"].data
        ) as r:
            self.bot.print("[HelpUpdater]", await r.json())

    @tasks.loop(seconds=30)
    async def update_help(self):
        try:
            async with self.bot.session.get(
                f"{self.bot.get_url()}/api/ping"
            ) as r:
                if (await r.text()) == "pong":
                    self.bot.dispatch("update_api")
        except Exception:
            self.bot.backend = False
        else:
            self.bot.backend = True

    @commands.Cog.listener()
    async def on_update_api(self):
        await self.update_help_web()

    def cog_unload(self):
        self.update_help.cancel()

    def search(self, word: str, lang: str) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        # 指定された言葉で検索する関数です。
        on_name, on_doc = [], []
        for category_name in self.help:
            for cmd in self.help[category_name]:
                if word in cmd:
                    on_name.append((category_name, cmd))
                if len(self.help[category_name][cmd][lang]) >= 2:
                    if word in self.help[category_name][cmd][lang][1]:
                        on_doc.append((category_name, cmd))
        return on_name, on_doc

    async def _help(self, ctx, word, interaction=None):
        self.help = self.bot.cogs["DocHelp"].data
        lang = self.bot.cogs["Language"].get(ctx.author.id)
        command_matched = convert_commands(self.help, word)

        if word is None:
            url = "https://free-rt.com/help.html"
            embed = discord.Embed(
                title={
                    "ja": "Help - カテゴリー選択", "en": "Help - Category Select"
                },
                description={
                    "ja": f"カテゴリーを選択するとそのカテゴリーにあるコマンドが表示されます。\nまたこちらからも見れます：{url}"
                          "\n[こちら](https://rt-team.github.io/ja/notes/help)を見るとヘルプをよく理解できるようになれるかもしれません。"
                          "そしてスラッシュコマンドは少し特殊なので[こちら](https://free-rt.github.io/notes/slash_table)を確認してください。\n"
                          "Free RTを使用した場合は[利用規約](https://free-rt.com/terms.html)に同意したことになります。\n"
                          "また、プライバシーポリシーは[こちら](https://free-rt.com/privacy.html)から確認できます。",
                    "en": f"Selecting a category will show you the commands in that category. \nYou can also see them here: {url}\n"
                          "You may be able to understand the help better by looking at [here](https://free-rt.github.io/en/notes/help).\n"
                          "By using Free RT, you agree to the [Terms of Use](https://free-rt.com/terms.html).\n"
                          "You can also view our privacy policy at [here](https://free-rt.com/privacy.html)."
                }, color=self.bot.colors["normal"]
            )
            view = HelpView(ctx.author.id, lang, self.help)
            await ctx.send(embed=embed, view=view)
        elif word in self.help:
            # カテゴリ名と一致したとき。
            embed = get_category_help(self.bot, self.help, word, lang)
            view = HelpView(ctx.author.id, lang, self.help)
            await ctx.send(embed=embed, view=view)
        elif command_matched:
            # コマンド名と一致したとき。
            commands = convert_commands(self.help)
            embed = get_command_help(self.bot, commands, word, lang)
            view = HelpView(ctx.author.id, lang, self.help, command_matched)
            await ctx.send(embed=embed, view=view)
        else:
            # 検索結果を表示する。
            on_name, on_doc = self.search(word, lang)
            embed = discord.Embed(
                title="検索結果", color=self.bot.colors["normal"]
            )
            for name, value in (("名前部分一致", on_name), ("説明部分一致", on_doc)):
                embed.add_field(
                    name=name,
                    value=("\n".join(
                        f"`{n}` {self.help[category][n][lang][0]}"
                        for category, n in value)
                        if value else "見つかりませんでした。")
                )
            await ctx.send(embed=embed)

    @commands.command(
        name="help", aliases=["h", "Help_me,_ERINNNNNN!!", "たすけて！"],
        extras={
            "headding": {"ja": "Helpを表示します。",
                         "en": "Get help."},
            "parent": "RT"
        }, description="ヘルプを表示します。"
    )
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def dhelp(
        self, ctx, *, word=None
    ):
        """!lang ja
        --------
        コマンドの使い方が載っているヘルプを表示します。  
        また、[ここ](https://free-rt.github.io/notes/help)を見るとコマンドの見方がよくわかるかもしれません。

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
            If a word that is not a command name is specified, a search will be performed.

        Aliases
        -------
        `h`"""
        if not "DocHelp" in self.bot.cogs:
            return await ctx.send(
                {"ja": "現在起動中のためヘルプを表示できません。", "en": "Help is not available because the bot is still loading."}
            )
        await self._help(ctx, word)


async def setup(bot):
    await bot.add_cog(Help(bot))
