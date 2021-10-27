# RT - Twitter

from typing import TYPE_CHECKING, Dict, Tuple, List

from discord.ext import commands
import discord

from tweepy.asynchronous import AsyncStream

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop, Task
    from tweepy.models import Status
    from aiomysql import Pool
    from rtlib import Backend


class DataManager:

    TABLE = "TwitterNotification"
    DEFAULT_MAX = 5

    def __init__(self, loop: "AbstractEventLoop", pool: "Pool"):
        self.pool = pool
        loop.create_task(self._prepare_table())

    async def _prepare_table(self):
        # テーブルを準備します。
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""CREATE TABLE IF NOT EXISTS {self.TABLE} (
                        GuildID BIGINT, ChannelID BIGINT, UserName TEXT
                    );"""
                )
                await self._update_users(cursor)
        self.start_stream()

    async def _read(self, cursor, channel, username):
        await cursor.execute(
            f"SELECT * FROM {self.TABLE} WHERE ChannelID = %s AND UserName = %s;",
            (channel.id, username)
        )
        return await cursor.fetchone()

    async def write(self, channel: discord.TextChannel, username: str) -> None:
        "設定を保存します。"
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                assert not await self._read(cursor, channel, username), "既に設定されています。"
                await cursor.execute(
                    f"SELECT * FROM {self.TABLE} WHERE GuildID = %s;",
                    (channel.guild.id,)
                )
                assert len(await cursor.fetchall()) <= self.DEFAULT_MAX, "追加しすぎです。"
                await cursor.execute(
                    f"INSERT INTO {self.TABLE} VALUES (%s, %s, %s);",
                    (channel.guild.id, channel.id, username)
                )

    async def delete(self, channel: discord.TextChannel, username: str) -> None:
        "設定を削除します。"
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                assert await self._read(cursor, channel, username), "その設定はありません。"
                await cursor.execute(
                    f"DELETE FROM {self.TABLE} WHERE ChannelID = %s AND UserName = %s;",
                    (channel.id, username)
                )

    async def _update_users(self, cursor):
        await cursor.execute(
            f"SELECT ChannelID, UserName FROM {self.TABLE};"
        )
        self.users = {
            username: channel_id
            for channel_id, username in await cursor.fetchall()
        }

    async def update_users(self) -> List[Tuple[int, str]]:
        "設定のキャッシュを更新します。"
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await self._update_users(cursor)


class NewAsyncStream(AsyncStream):

    BASE_URL = "https://twitter.com/{}/status/{}"

    def __init__(self, cog: "TwitterNotification", *args, **kwargs):
        self.cog = cog
        self.connected = False
        super().__init__(*args, **kwargs)

    def filter(self, *args, **kwargs):
        self.connected = True
        super().filter(*args, **kwargs)

    def disconnect(self, *args, **kwargs):
        self.connected = False
        super().disconnect(*args, **kwargs)

    async def on_status(self, status: "Status"):
        if status.user.screen_name in self.users:
            channel = self.cog.bot.get_channel(self.users[status.user.screen_name])
            if channel:
                try:
                    await channel.send(
                        f'{"🔁 Rewteeted" if status.retweeted else ""}\n' \
                        + self.BASE_URL.format(status.user.screen_name, status.id_str)
                    )
                except Exception as e:
                    print("Error on TwitterAsyncStream:", e)
            else:
                # もし通知するチャンネルが見当たらない場合はその設定を削除する。
                await self.cog.delete(
                    self.users[status.user.screen_name], status.user.screen_name
                )


class TwitterNotification(commands.Cog, DataManager, NewAsyncStream):

    task: "Task"

    def __init__(self, bot: "Backend"):
        self.bot = bot
        self.users: Dict[str, int] = {}
        super(commands.Cog, self).__init__(self.bot.loop, self.bot.mysql.pool)
        super(DataManager, self).__init__(self, **self.bot.secret["twitter"])

    def start_stream(self, disconnect: bool = False) -> None:
        "Twitterのストリームを開始します。"
        if disconnect and self.connected:
            self.disconnect()
        if self.users:
            self.task = self.filter(follow=list(self.users.values()))

    def cog_unload(self):
        if self.connected:
            self.disconnect()

    @commands.group(aliases=["ツイッター", "tw"])
    async def twitter_(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.reply("使用方法が違います。 / It is used in different ways.")

    @twitter_.command("set", aliases=["s", "設定"])
    @commands.has_permissions(manage_channels=True, manage_webhooks=True)
    @commands.cooldown(1, 60, commands.BucketType.channel)
    async def set_(self, ctx, onoff: bool, *, username):
        await ctx.trigger_typing()
        try:
            if onoff:
                await self.write(ctx.channel, username)
            else:
                await self.delete(ctx.channel, username)
        except AssertionError:
            await ctx.reply(
                {"ja": "既に設定されています。\nまたは設定しすぎです。",
                "en": "The username is already set.\nOr it is set too high."} \
                if onoff else {
                    "ja": "設定されていません。",
                    "en": "The username is not set yet."
                }
            )
        else:
            await self.update_users()
            self.start_stream(True)
            await ctx.reply("Ok")

    @twitter_.command("list", aliases=["l", "一覧"])
    async def list_(self, ctx):
        await ctx.reply(
            embed=discord.Embed(
                title="Twitter",
                description="\n".join(
                    f"<#{channel_id}>：{username}"
                    for username, channel_id in self.users.items()
                )
            )
        )


def setup(bot):
    bot.add_cog(TwitterNotification(bot))