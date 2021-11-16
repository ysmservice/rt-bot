# RT - Captcha

from typing import TypedDict, Dict

from discord.ext import commands, tasks
import discord

from time import time

from rtlib import RT, DatabaseManager, websocket
from .image_captcha import ImageCaptcha
from .word_captcha import WordCaptcha
from .web_captcha import WebCaptcha


class DataManager(DatabaseManager):
    def __init__(self, db):
        self.db = db

    async def init_table(self, cursor):
        await cursor.create_table(
            "captcha", {
                "GuildID": "BIGINT",
                "ChannelID": "BIGINT",
                "Mode": "TEXT",
                "RoleID": "BIGINT",
                "Extras": "TEXT"
            }
        )

    async def save(
        self, cursor, channel: discord.TextChannel,
        mode: str, role_id: int, extras: dict
    ) -> None:
        target = {"GuildID": channel.guild.id}
        change = {
            "ChannelID": channel.id, "Mode": mode,
            "RoleID": role_id, "Extras": extras
        }
        if await cursor.exists("captcha", target):
            await cursor.update_data("captcha", change, target)
        else:
            target.update(change)
            await cursor.insert_data("captcha", target)

    async def delete(self, cursor, channel: discord.TextChannel) -> None:
        target = {"GuildID": channel.guild.id, "ChannelID": channel.id}
        if await cursor.exists("captcha", target):
            await cursor.delete("captcha", target)

    async def load(self, cursor, guild_id: int) -> tuple:
        target = {"GuildID": guild_id}
        if await cursor.exists("captcha", target):
            if (row := await cursor.get_data("captcha", target)):
                return row
        return ()


class Captchas(TypedDict):
    image: ImageCaptcha
    word: WordCaptcha
    web: WebCaptcha


class ClickCaptchaView(discord.ui.View):
    def __init__(self, bot_id: int, *args, **kwargs):
        self.bot_id = bot_id
        kwargs["timeout"] = kwargs.get("timeout", None)
        super().__init__(*args, **kwargs)

    @discord.ui.button(
        label="認証",  custom_id="ClickCaptchaButton",
        style=discord.ButtonStyle.primary, emoji="🔎",
    )
    async def captcha(self, _, interaction: discord.Interaction):
        if interaction.message.author.id == self.bot_id:
            role = interaction.guild.get_role(
                int(interaction.message.content)
            )
            content = ""
            if role:
                if interaction.user.get_role(role.id) is None:
                    try:
                        await interaction.user.add_roles(role)
                    except discord.Forbidden:
                        content = "権限がないのでロールを付与できませんでした。"
                    except discord.HTTPException as e:
                        content = f"何かエラーが発生してロールを付与できませんでした。\ncode:{e}"
                    else:
                        content = "ロールを付与しました。"
            else:
                content = "付与するロールが見つからなかったので認証に失敗しました。"
            if content:
                await interaction.response.send_message(
                    content=content, ephemeral=True
                )


class Captcha(commands.Cog, DataManager):
    def __init__(self, bot: RT):
        self.bot = bot
        self.view = ClickCaptchaView(self.bot.user.id)
        self.bot.add_view(self.view)
        self.captchas: Captchas = {
            "image": ImageCaptcha(self),
            "word": WordCaptcha(self),
            "web": WebCaptcha(
                self, (
                    self.bot.secret["test_hCaptcha"]
                    if bot.test else
                    self.bot.secret["hCaptcha"]
                )
            )
        }
        self.sitekey = (
            "20000000-ffff-ffff-ffff-000000000002"
            if bot.test else
            "0a50268d-fa1e-405f-9029-710309aad1b0"
        )
        self.queue_killer.start()
        self.cache: Dict[str, float] = {}
        self.bot.loop.create_task(self.init_database())

    @commands.command(
        aliases=["ca", "認証", "きゃぷちゃ", "auth", "cpic"],
        extras={
            "headding": {
                "ja": "画像認証, 合言葉認証, ウェブ認証をサーバーに設定します。",
                "en": "Image captcha, Password captcha, Web Captcha (hCaptcha)"
            },
            "parent": "ServerSafety"
        }
    )
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def captcha(self, ctx, mode, *, role: discord.Role = None):
        """!lang ja
        --------
        認証を設定します。  
        認証を設定することでサーバーに参加した人がセルフBot(自動で動くユーザー)じゃないなら喋れるようにするといったことができます。  
        ※自動で動くユーザーの大半が荒らし目的で動いています。  
        またこの機能の合言葉認証を使うことで合言葉を知っている人のみがサーバーで喋ることができるなどのこともできます。  
        認証をするチャンネルはこのコマンドを実行したチャンネルに設定されるので、このコマンドはウェルカムメッセージが送信されるチャンネルで実行しましょう。

        Parameters
        ----------
        mode : image, web, click, 左の三つ以外の場合は合言葉
            設定する認証の種類です。  
            `image`が画像認証で実行したチャンネルに送信される画像にある数字を正しく入力するという認証です。  
            `web`がhCaptchaを利用したウェブでの本格認証です。  
            `click`がボタンを押したらロールを付与するというボタンのメッセージを作ります。  
            `click`の場合強度は手軽ですがそこまで高くないです。  
            上記二つ以外を入力した場合はその入力した言葉を使った合言葉認証で設定されます。  
            もし設定をオフにするなら`off`にして役職(role)を指定しないでください。
        role : 役職名または役職のメンション, optional
            認証成功時に付与する役職の名前またはメンションです。  
            もし設定を解除する場合はこれを指定しないでください。

        Examples
        --------
        設定する際
        `rt!captcha web @認証済み`  
        ウェブ認証で認証成功時には`認証済み`という役職を付与する用に設定します。
        
        解除する際
        `rt!captcha off`
        認証を有効にしているチャンネルで実行すると、設定を解除できます。

        Notes
        -----
        認証をするチャンネルは認証済みの人から見えないようにするのを推奨します。  
        そうすれば荒らしをする自動で動くユーザーが来た際に荒らしの影響を認証済みユーザーは受けません。  
        このコマンドを実行することができるのは管理者権限を持っている人のみです。

        !lang en
        --------
        Set up authentication.  
        By setting up authentication, you can allow people who join the server to speak if they are not self-bots (users who run automatically).  
        The majority of auto-automated users are working for the purpose of trolling.  
        You can also use the password authentication feature to allow only those who know the password to speak on the server by this function.  
        The channel for authentication will be set to the channel where this command is executed, so this command should be executed on the channel where the welcome message will be sent.

        Parameters
        ----------
        mode : image, web, or password if other than the two on the left
            The type of authentication to set.  
            `image` is image authentication, which means that you must correctly enter the numbers in the image sent to the channel you are running on.  
            The `web` is full-fledged authentication on the web using hCaptcha.  
            If you enter something other than two above, mode will be set `Password(You had entered word in this command.) Mode`.  
        role : Name of the role or mention of the role
            The name of the role to be assigned upon successful authentication.

        Examples
        --------
        `rt!captcha web @authenticated`.  
        Set web authentication to give the role `authenticated` on successful authentication.

        Notes
        -----
        It is recommended to make the authenticating channel invisible to authenticated users and set slowmode.  
        This way, if an automated vandal comes along, the authenticated users will not be affected by the vandalism.  
        This command can only be executed by someone with administrative privileges."""
        if role is None:
            await self.delete(ctx.channel)
        elif mode == "click":
            return await ctx.send(
                str(role.id), embed=discord.Embed(
                    title="ワンクリック認証",
                    description="下のボタンをクリックすることで認証できます。",
                    color=self.bot.colors["normal"]
                ), view=self.view
            )
        else:
            extras = ""
            if mode not in self.captchas:
                extras = mode
                mode = "word"
            await self.save(ctx.channel, mode, role.id, extras)
        await ctx.reply("Ok")

    async def init_database(self):
        super(commands.Cog, self).__init__(
            self.bot.mysql
        )
        await self.init_table()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if (not self.bot.is_ready() or member.bot
                or (key := f"{member.guild.id}-{member.id}") in self.cache):
            # 準備中,Botまたは既に認証を送信したのなら何もしない。
            return

        row = await self.load(member.guild.id)
        if len(row) >= 4:
            captcha = self.captchas[row[2]]
            channel = discord.utils.get(member.guild.text_channels, id=row[1])
            if channel:
                await captcha.captcha(channel, member)
            self.cache[key] = time() + 3600

    def cog_unload(self):
        self.queue_killer.cancel()

    @tasks.loop(minutes=1)
    async def queue_killer(self):
        # 放置されて溜まってしまっている認証queueを削除する。
        now = time()
        for captcha in list(self.captchas.values()):
            for key in list(captcha.queue.keys()):
                if now - captcha.queue[key][1] > 3600:
                    del captcha.queue[key]
        # 溜まったキャッシュを削除する。
        for key, timeout in list(self.cache.items()):
            if timeout <= now:
                del self.cache[key]

    def remove_cache(self, member: discord.Member) -> None:
        del self.cache[f"{member.guild.id}-{member.id}"]

    @websocket.websocket("/api/captcha", auto_connect=True, reconnect=True,)
    async def websocket_(self, ws: websocket.WebSocket, _):
        await ws.send("on_ready")

    @websocket_.event("on_success")
    async def on_seccess(self, ws: websocket.WebSocket, user_id: str):
        for key, (_, _, channel) in list(self.captchas["web"].queue.items()):
            if key.endswith(user_id):
                await self.captchas["web"].success_user(
                    {
                        "user_id": int(user_id), "guild_id": int(key[:key.find("-")]),
                        "channel": channel
                    }
                )
            del self.captchas["web"].queue[key]


def setup(bot):
    bot.add_cog(Captcha(bot))
