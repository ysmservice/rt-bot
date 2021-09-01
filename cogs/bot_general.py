# RT - Bog General

from discord.ext import commands, tasks
import discord

from traceback import TracebackException
from rtlib.ext import Embeds, componesy
from time import time


ERROR_CHANNEL = 842744343911596062

INFO_DESC = {
    "ja": """どうもRTという新時代Botです。
このBotは既にある色々な機能や今までにない機能を取り入れた多機能型Botです。
チャンネルステータスやウェルカムメッセージももちろん、変更可能このの読み上げや常に一番下にくるメッセージなど色々あります。これ翻訳できず
ほとんどこのBotで済むようなBotを目指してる。""",
    "en": """Hi I am RTBOT. This is for new year.
    This bot is many function and never before function in this Bot.
    Of course channelstatus, welcome message
    I am aiming for a bot that can almost be done with this bot"""
}
INFO_ITEMS = (("INVITE", {"ja": "招待リンク", "en": "invite link"}),
              ("SS", {"ja": "サポートサーバー", "en": "support server"}),
              ("URL", {"ja": "RTのウェブサイト", "en": "RT offical website"}),
              ("GITHUB", {"ja": "Github", "en": "Github"}))
INFO_INVITE = "https://discord.com/api/oauth2/authorize?client_id=716496407212589087&permissions=8&scope=bot"
INFO_SS, INFO_URL = "https://discord.gg/ugMGw5w", "https://rt-bot.com"
INFO_GITHUB = """* [RT-Team](https://github.com/RT-Team)
* [RT-Backend](https://github.com/RT-Team/rt-backend)
* [RT-Frontend](https://github.com/RT-Team/rt-frontend)"""

CREDIT_ITEMS = (("DEV", {"ja": "主な開発者", "en": "main developer"}),
                ("DESIGN", {"ja": "絵文字デザイン", "en": "emoji designer"}),
                ("ICON", {"ja": "RTのアイコン", "en": "RT's icon"}),
                ("LANGUAGE", {"ja": "プログラミング言語", "en": "programing language"}),
                ("SERVER", {"ja": "サーバーについて", "en": "about server"}),
                ("ETC", {"ja": "その他", "en": "etc"}))
CREDIT_DEV = """<:tasren:731263470636498954> tasuren [WEBSITE](http://tasuren.f5.si)
<:takkun:731263181586169857> Takkun [SERVER](https://discord.gg/VX7ceJw)
<:Snavy:788377881092161577> Snavy [SERVER](https://discord.gg/t8fsvk3)"""
CREDIT_DESIGN = """<:yutam:732948166881575022> YUTAM
<:omochi_nagamochi:733618053631311924> 餅。"""
CREDIT_ICON = "Made by Takkun `CC BY-SA 4.0`"
CREDIT_LANGUAGE = {
    "ja": "使用言語：Python, 使用ライブラリ：discord.py",
    "en": "using language:Python, using library:discord.py"
}
CREDIT_SERVER = {
    "ja": "サーバーOS：Arch Linux\nSnavyさんが貸してくれています。感謝感激です！",
    "en": "server os:Arch Linux\nSnavy is lend server to me. Thank you to Snavy "
}
CREDIT_ETC = {
    "ja": "* Githubのコントリビューター達。\n* 主な翻訳協力者であるDMSくん。\nありがとうございます。",
    "en": "*Github's sontributors. \n* This bot is translate by DMS. \n Thank you"
}


class BotGeneral(commands.Cog):

    STATUS_TEXTS = (
        ("{}help | {} servers", lambda bot: len(bot.guilds)),
        ("{}help | {} users", lambda bot: len(bot.users))
    )

    def __init__(self, bot):
        self.bot, self.rt = bot, bot.data

        # RT情報Embedsを作る。
        embeds = self.info_embeds = []
        # RTの情報のEmbedを作る。
        embed = discord.Embed(
            title="RT 情報",
            description=INFO_DESC,
            color=self.bot.colors["normal"]
        )
        for item_variable_name, item_name in INFO_ITEMS:
            embed.add_field(
                name=item_name, value=eval("INFO_" + item_variable_name),
                inline=False
            )
        embeds.append(embed)
        # クレジットのEmbedを作る。
        embed = discord.Embed(
            title="RT クレジット",
            color=self.bot.colors["normal"]
        )
        for item_variable_name, item_name in CREDIT_ITEMS:
            embed.add_field(
                name=item_name, value=eval("CREDIT_" + item_variable_name),
                inline=False
            )
        embeds.append(embed)
        # 使用しているライブラリ
        with open("requirements.txt") as f:
            libs = f.read()
        embed = discord.Embed(
            title="使用しているライブラリ",
            description=f"```md\n{libs}\n```",
            color=self.bot.colors["normal"]
        )
        embeds.append(embed)
        del embed, libs

        self._now_status_index = 0
        self._start_time = time()
        self.status_updater.start()

    @commands.Cog.listener()
    async def on_ready(self):
        self.on_error_channel = self.bot.get_channel(ERROR_CHANNEL)

    def _get_ping(self) -> int:
        # pingを返します。
        try:
            return round(self.bot.latency * 1000)
        except OverflowError:
            return 200

    def cog_unload(self) -> None:
        self.status_updater.cancel()

    @tasks.loop(seconds=60)
    async def status_updater(self) -> None:
        # RTのステータスを更新するループです。
        await self.bot.wait_until_ready()

        await self.bot.change_presence(
            activity=discord.Activity(
                name=(now := self.STATUS_TEXTS[self._now_status_index])[0]
                    .format(self.bot.command_prefix[0], now[1](self.bot)),
                type=discord.ActivityType.watching, state="RT Discord Bot",
                details=f"PING：{self._get_ping()}\n絶賛稼働中...",
                timestamps={"start": self._start_time},
                buttons={"label": "RTのホームページに行く！", "url": "https://rt-bot.com/"}
            )
        )

        self._now_status_index = 0 if self._now_status_index else 1

    @commands.command(
        extras={"headding": {"ja": "レイテンシを表示します。", "en": "Show you RT latency."},
                "parent": "RT"},
        slash_command=True,
        description="レイテンシを表示します。 / Show you RT latency.")
    async def ping(self, ctx):
        """!lang ja
        --------
        RTのレイテンシを表示します。  
        返信された数字が400以降だとネット回線が悪いです。

        !lang en
        --------
        You can view RT latency.  
        If latency is over to 400, network is bad."""
        await ctx.reply(
            {"ja": f"現在のRTのレイテンシ：{self._get_ping()}ms",
             "en": f"Pong! {self._get_ping()}ms"}
        )

    @commands.command(
        extras={"headding": {"ja": "クレジットを表示します。", "en": "It can view credit."},
                "parent": "RT"},
        aliases=["credit", "invite", "about", "情報", "じょうほう"])
    @commands.cooldown(1, 180, commands.BucketType.user)
    async def info(self, ctx, secret_arg = None):
        """!lang ja
        --------
        RTの情報を表示します。  
        RTの基本情報(招待リンク,ウェブサイトURL)やクレジットなどを確認することができます。  
        このコマンドは三分に一度実行可能です。
        
        !lang en
        --------
        ..."""
        if secret_arg is None:
            await ctx.reply(
                embeds=Embeds("RtInfo", ctx.author, 180, self.info_embeds)
            )
        else:
            await ctx.reply(f"{secret_arg}...、あなた何奴！？")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # エラー時のメッセージ。翻訳はdescriptionのみ。
        kwargs, color, content = {}, self.bot.colors["error"], "エラー"
        if isinstance(error, commands.errors.CommandNotFound):
            title = "404 Not Found"
            description = {"ja": ("そのコマンドが見つかりませんでした。\n"
                                  + "`rt!help <word>`で検索が可能です。"),
                           "en": "It can't found that command.\n`rt!help <word>`This can search command"}
            color = self.bot.colors["unknown"]
        elif isinstance(error, (commands.errors.BadArgument,
                        commands.errors.MissingRequiredArgument,
                        commands.errors.ArgumentParsingError,
                        commands.errors.TooManyArguments)):
            title = "400 Bad Request"
            description = {"ja": "コマンドの引数が適切ではありません。\nまたは必要な引数が足りません。",
                           "en": "It's command's function is bad."}
        elif isinstance(error, commands.errors.CommandOnCooldown):
            title = "429 Too Many Requests"
            description = {"ja": ("現在このコマンドはクールダウンとなっています。\n"
                                  + "{:.2f}秒後に実行できます。".format(
                                      error.retry_after)),
                           "en": ("...\n"
                                  + "{:.2f}".format(
                                      error.retry_after))}
            color = self.bot.colors["unknown"]
        elif isinstance(error, (commands.errors.MemberNotFound,
                        commands.errors.UserNotFound)):
            title = "400 Bad Request"
            description = {"ja": "指定されたユーザーが見つかりませんでした。",
                           "en": "I can't found that user."}
        elif isinstance(error, commands.errors.ChannelNotFound):
            title = "400 Bad Request"
            description = {"ja": "指定されたチャンネルが見つかりませんでした。",
                           "en": "I can't found that channel"}
        elif isinstance(error, commands.errors.RoleNotFound):
            title = "400 Bad Request"
            description = {"ja": "指定されたロールが見つかりませんでした。",
                           "en": "I can't found that role."}
        elif isinstance(error, commands.errors.BadBoolArgument):
            title = "400 Bad Request"
            description = {"ja": ("指定された真偽値が無効です。\n"
                                  + "有効な真偽値：`on/off`, `true/false`, `True/False`"),
                           "en": ("The specified boolean value is invalid\n"
                                  + "...:`on/off`, `true/false`, `True/False`")}
        elif isinstance(error, commands.errors.MissingPermissions):
            title = "403 Forbidden"
            description = {"ja": "あなたの権限ではこのコマンドを実行することができません。",
                           "en": "You can't do this command. Because you need permission"}
        elif isinstance(error, commands.errors.MissingRole):
            title = "403 Forbidden"
            description = {"ja": "あなたはこのコマンドの実行に必要な役職を持っていないため、このコマンドを実行できません。",
                           "en": "You can't do this command. Because you need permission"}
        else:
            error_message = "".join(
                TracebackException.from_exception(error).format())

            # テストモードなら問答無用でエラーを出力する。
            if self.bot.command_prefix[0] == "r2!":
                print(error_message)
            else:
                # RTサーバーにエラーを通知する。
                await self.on_error_channel.send(
                    (f"**エラーが発生しました。**\nGuild: {ctx.guild.name}, "
                    + f"User: {ctx.author.name}\nコマンド名：{ctx.command.qualified_name}"
                    + content)
                )

            title = "500 Internal Server Error"
            description = {
                "ja": (f"コマンドの実行中にエラーが発生しました。\n"
                       + f"```python\n{error_message}\n```"),
                "en": (f"...\n"
                       + f"```python\n{error_message}\n```"),
            }

            view = componesy.View("InternalServerErrorView", timeout=60)
            view.add_item(
                "link_button", style=discord.ButtonStyle.link,
                label="サポートサーバー / SupportServer", url=INFO_SS
            )
            kwargs["view"] = view

        kwargs["embed"] = discord.Embed(
            title=title, description=description, color=color)
        await ctx.send(f"{ctx.author.mention} " + content, **kwargs)


def setup(bot):
    bot.add_cog(BotGeneral(bot))
