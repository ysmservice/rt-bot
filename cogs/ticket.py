# RT - Ticket

from typing import TYPE_CHECKING, Union, Optional, Dict

from discord.ext import commands, tasks
import discord

from rtlib import componesy
from time import time

if TYPE_CHECKING:
    from aiomysql import Pool

    class NewInteraction(discord.Interaction):
        member: Union[discord.Member, discord.User]


class RealNewInteraction:
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.member = interaction.user

    def __getattr__(self, name):
        return getattr(self.interaction, name)


# 定数を設定する。
TITLE = "[Ticket]"
CUSTOM_ID = "rt_ticket"
COOLDOWN = 150
TABLE = "TicketMessage"
VIEW = componesy.View("TicketView")
VIEW.add_item(
    discord.ui.Button, None, label="Ticket",
    emoji="🎫", custom_id=CUSTOM_ID
)
VIEW = VIEW()


class DataManager:
    def __init__(self, pool: "Pool"):
        self.pool = pool

    async def prepare_table(self) -> None:
        """テーブルを作成します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""CREATE TABLE IF NOT EXISTS {TABLE} (
                        GuildID BIGINT PRIMARY KEY NOT NULL,
                        ChannelID BIGINT, Content TEXT
                    );"""
                )

    async def set_message(self, channel: discord.TextChannel, content: str) -> None:
        """チケット作成時に送信するメッセージを設定します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""INSERT INTO {TABLE}
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        ChannelID = %s, Content = %s;""",
                    (channel.guild.id, channel.id,
                     content, channel.id, content)
                )

    async def delete_message(self, guild_id: int) -> None:
        """指定されたサーバーに設定されているメッセージを削除します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT GuildID FROM {TABLE} WHERE GuildID = %s;",
                    (guild_id,)
                )
                assert await cursor.fetchone(), "見つかりませんでした。"
                await cursor.execute(
                    f"DELETE FROM {TABLE} WHERE GuildID = %s;",
                    (guild_id,)
                )

    async def read(self, guild_id: int) -> Optional[str]:
        """指定されたサーバーに設定されているメッセージを読み込みます。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT Content FROM {TABLE} WHERE GuildID = %s;",
                    (guild_id,)
                )
                if (row := await cursor.fetchone()):
                    return row[0]


class Ticket(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot
        self.cooldown: Dict[int, float] = {}
        self.cooldown_killer.start()
        self.bot.loop.create_task(self.init_database())

    async def init_database(self):
        # データベースの準備をする。
        super(commands.Cog, self).__init__(self.bot.mysql.pool)
        await self.prepare_table()

    def cog_unload(self):
        self.cooldown_killer.cancel()

    @tasks.loop(minutes=5)
    async def cooldown_killer(self):
        # 放置されたクールダウンのキャッシュは削除する。
        now = time()
        for mid in list(self.cooldown.keys()):
            if self.cooldown[mid] <= now:
                del self.cooldown[mid]

    @commands.command(
        extras={
            "headding": {
                "ja": "チケットチャンネル作成用のパネルを作成します。",
                "en": "Ticket panel"
            }, "parent": "ServerPanel"
        }
    )
    @commands.has_permissions(manage_channels=True)
    async def ticket(self, ctx, title, description, *, role: discord.Role = None):
        """!lang ja
        --------
        チケットチャンネル作成用のパネルを作成します。

        Parameters
        ----------
        title : str, default 
            チケットパネルのタイトルです。
        description : str
            チケットパネルの説明欄に入れる文章です。  
            改行や空白を含めたい場合は`"`で文章を囲んでください。
        role : 役職名または役職のメンション, optional
            作成されるチケットチャンネルを見ることのできる役職です。  
            指定しない場合は管理者権限を持っている人とチケットチャンネル作成者本人のみが見れます。

        Notes
        -----
        このコマンドはチャンネル管理権限がある人でしか実行できません。  
        もしこのパネルを無効化したい場合は単純に作成したパネルを削除すれば良いです。  
        チケットチャンネル作成時に何かメッセージを送信してほしい場合は、チケットのあるチャンネルで以下のコマンドで設定できます。
        ```
        rt!tfm メッセージ内容 (もしオフにしたい場合は`off`)
        ```
        ※一つのサーバーにつき一つまで設定が可能です。

        Examples
        --------
        `rt!ticket 問い合わせ モデレーター`

        !lang en
        --------
        Creates a panel for creating a ticket channel.

        Parameters
        ----------
        title : str, default 
            The title of the ticket panel.
        description : str
            The text to put in the description field of the ticket panel.  
            If you want to include line breaks or spaces, enclose the text with `"`.
        role : name of the role or a mention of the role, optional
            The role that can see the ticket channel being created.  
            If not specified, only the administrator and the creator of the ticket channel will be able to see it.

        Notes
        -----
        This command can only be executed by someone with channel management privileges.  
        If you want to disable this panel, you can simply delete the panel you created.  
        If you want some message to be sent when a ticket channel is created, you can set it in the channel with the ticket by using the following command.
        ```
        rt!tfm Message content (or `off` if you want to turn it off)
        ```

        Examples
        --------
        `rt!ticket query moderator`"""
        if ctx.guild and ctx.channel.category and str(ctx.channel.type) == "text":
            embed = discord.Embed(
                title=title,
                description=description,
                color=self.bot.colors["normal"]
            )
            await ctx.webhook_send(
                username=ctx.author.name, avatar_url=ctx.author.avatar.url,
                content=f"RTチケットパネル, {getattr(role, 'id', '...')}",
                embed=embed, wait=True, replace_language=False, view=VIEW
            )
        else:
            await ctx.reply(
                {"ja": "このコマンドはカテゴリーにあるテキストチャンネルのみ動作します。",
                 "en": "This command can run on only text channel."}
            )

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def tfm(self, ctx: commands.Context, *, content: Union[bool, str]):
        # チケットメッセージ設定用コマンドです。
        await ctx.trigger_typing()
        if isinstance(content, bool) and not content:
            try:
                await self.delete_message(ctx.guild.id)
            except AssertionError:
                return await ctx.reply(
                    {"ja": "まだチケットメッセージは設定されていません。",
                     "en": "Ticket message is not set yet."}
                )
        else:
            await self.set_message(ctx.channel, content)
        await ctx.reply("Ok")

    def make_channel_name(self, name: str) -> str:
        # チケットチャンネル用の名前を作る関数です。
        return (name[:90] if len(name) > 90 else name) + "-rtチケット"

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data.get("custom_id", "") == CUSTOM_ID:
            # ボタンによるチケットチャンネル作成もする。
            try:
                await interaction.response.defer()
            except:
                pass
            finally:
                await self.on_ticket(RealNewInteraction(interaction))

    async def on_ticket(self, payload: Union["NewInteraction", discord.RawReactionActionEvent]):
        if ((hasattr(payload, "emoji") and str(payload.emoji) != "🎫") or payload.member.bot
                or not payload.message.embeds or not payload.message.guild
                or not payload.message.content.startswith("RTチケットパネル, ")):
            return

        # リアクションを追加/削除した人の名前でチケットチャンネル名を作る。
        channel_name = self.make_channel_name(payload.member.display_name)
        # リアクションを押した人が既にチャンネルを作成している場合はそのチャンネルを取得する。
        channel = discord.utils.get(
            payload.message.guild.text_channels,
            name=channel_name
        )

        if channel:
            # もし既にチケットチャンネルが存在するならそのチャンネルの削除を行う。
            await channel.delete(reason=f"{TITLE}チケット削除のため。")
        else:
            # もしリアクションが押されたなら。
            # クールダウンが必要ならチャンネルを作成しない。
            if (error := (now := time()) - self.cooldown.get(payload.member.id, 0.0)) < COOLDOWN:
                await payload.member.send(
                    {"ja": f"{payload.member.mention}, チケットチャンネルの作成にクールダウンが必要なため{error}秒待ってください。",
                     "en": f"{payload.member.mention}, It want cooldown, please wait for {error} seconds."},
                    delete_after=5, target=payload.member.id
                )
            else:
                self.cooldown[payload.member.id] = now

                # チケットチャンネルの作成に必要な情報を集める。
                role = (
                    payload.message.guild.get_role(
                        int(payload.message.content[11:])
                    ) if len(payload.message.content) > 15 else None
                )
                # overwritesを作る。
                perms = {
                    payload.message.guild.default_role: \
                        discord.PermissionOverwrite(read_messages=False),
                    payload.member: \
                        discord.PermissionOverwrite(read_messages=True)
                }
                if role:
                    # もしroleが指定されているならroleもoverwritesに追加する。
                    perms[role] = discord.PermissionOverwrite(read_messages=True)
                # チケットチャンネルを作成する。
                channel = await payload.message.channel.category.create_text_channel(
                    channel_name, overwrites=perms
                )
                await channel.send(
                    {"ja": f"{payload.member.mention}, ここがあなたのチャンネルです。",
                     "en": f"{payload.member.mention}, Here is your channel!"},
                    target=payload.member.id
                )
                if (first := await self.read(payload.guild_id)):
                    await channel.send(first)

    @commands.Cog.listener()
    async def on_full_reaction_add(self, payload):
        await self.on_ticket(payload)

    @commands.Cog.listener()
    async def on_full_reaction_remove(self, payload):
        await self.on_ticket(payload)


def setup(bot):
    bot.add_cog(Ticket(bot))
