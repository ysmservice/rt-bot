# RT - Twitter

from typing import TYPE_CHECKING, Dict, Tuple, List

from discord.ext import commands
import discord

from tweepy.asynchronous import AsyncStream
from aiohttp import client_exceptions
from asyncio import sleep, Event

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
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
        self.ready.set()

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


class TwitterNotification(commands.Cog, DataManager, AsyncStream):

    TWITTERID_HEADERS = {
        "authority": "tweeterid.com",
        "sec-ch-ua": "^\\^Microsoft",
        "accept": "*/*",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "x-requested-with": "XMLHttpRequest",
        "sec-ch-ua-mobile": "?0",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36 Edg/93.0.961.38",
        "sec-ch-ua-platform": "^\\^Windows^\\^",
        "origin": "https://tweeterid.com",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": "https://tweeterid.com/",
        "accept-language": "ja,en;q=0.9,en-GB;q=0.8,en-US;q=0.7",
    }
    BASE_URL = "https://twitter.com/{}/status/{}"

    def __init__(self, bot: "Backend"):
        self.bot = bot
        self.users: Dict[str, int] = {}
        self.ready: Event = Event()
        super(commands.Cog, self).__init__(self.bot.loop, self.bot.mysql.pool)
        super(DataManager, self).__init__(**self.bot.secret["twitter"])
        self.connected = False
        self.cache: Dict[str, str] = {}
        self.bot.loop.create_task(self.start_stream())

    def filter(self, *args, **kwargs):
        self.connected = True
        super().filter(*args, **kwargs)

    def disconnect(self, *args, **kwargs):
        self.connected = False
        super().disconnect(*args, **kwargs)

    async def get_user_id(self, username: str, retry: bool = False) -> str:
        "指定されたユーザーのIDを取得する。"
        print(1, username)
        if username in self.cache:
            return self.cache[username]
        else:
            try:
                async with self.bot.session.post(
                    "https://tweeterid.com/ajax.php",
                    headers=self.TWITTERID_HEADERS, data={"input": username}
                ) as r:
                    if (user_id := await r.text()) == "error":
                        return ""
                    else:
                        self.cache[username] = user_id
                        print(2, user_id)
                        return user_id
            except client_exceptions.ClientOSError as e:
                if retry:
                    raise e
                else:
                    await sleep(1)
                    return await self.get_user_id(username, True)

    async def on_status(self, status: "Status"):
        # ツイートを取得した際に呼ばれる関数です。
        print(status)
        if status.user.screen_name in self.users:
            print(self.users[status.user.screen_name])
            channel = self.bot.get_channel(self.users[status.user.screen_name])
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
                await self.delete(
                    self.users[status.user.screen_name], status.user.screen_name
                )

    async def start_stream(self, disconnect: bool = False) -> None:
        "Twitterのストリームを開始します。"
        if disconnect and self.connected:
            self.disconnect()
        if hasattr(self, "ready"):
            await self.ready.wait()
            del self.ready
        if self.users:
            self.filter(
                follow=[
                    await self.get_user_id(username) for username in self.users
                ]
            )

    def cog_unload(self):
        if self.connected:
            self.disconnect()

    @commands.group(aliases=["ツイッター", "tw"])
    async def twitter(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.reply("使用方法が違います。 / It is used in different ways.")

    @twitter.command("set", aliases=["s", "設定"])
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

    @twitter.command("list", aliases=["l", "一覧"])
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