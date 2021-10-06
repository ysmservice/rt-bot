# RT - Twitter

from discord.ext import commands, tasks

from aiohttp import client_exceptions
from rtlib import DatabaseManager
from bs4 import BeautifulSoup
from urllib import parse
from ujson import loads
from time import time
import asyncio


class DataManager(DatabaseManager):

    DB = "Twitter"
    LOG_DB = "TwitterSended"

    def __init__(self, db):
        self.db = db

    async def init_table(self, cursor) -> None:
        await cursor.create_table(
            self.DB, {
                "GuildID": "BIGINT", "ChannelID": "BIGINT",
                "UserName": "TEXT"
            }
        )
        await cursor.create_table(
            self.LOG_DB, {
                "ChannelID": "BIGINT",
                "TweetID": "BIGINT",
                "RegTime": "BIGINT"
            }
        )

    async def sended(self, cursor, channel_id: int, tweet_id: int) -> None:
        await cursor.insert_data(
            self.LOG_DB, {
                "ChannelID": channel_id, "TweetID": tweet_id,
                "RegTime": int(time())
            }
        )
        rows = await self._get_sended(cursor, channel_id)
        if len(rows) == 6:
            await cursor.delete(
                self.LOG_DB,
                {"ChannelID": channel_id, "TweetID": rows[0][1]}
            )

    async def _get_sended(self, cursor, channel_id: int) -> list:
        await cursor.cursor.execute(
            """SELECT * FROM {}
                WHERE ChannelID = %s
                ORDER BY RegTime ASC
                LIMIT 6;""".format(self.LOG_DB),
            (channel_id,)
        )
        return await cursor.cursor.fetchall()

    async def check(self, cursor, channel_id: int, tweet_id: int) -> bool:
        return await cursor.exists(
            self.LOG_DB, {"ChannelID": channel_id, "TweetID": tweet_id}
        )

    async def delete_sended(self, cursor, channel_id: int) -> None:
        target = {"ChannelID": channel_id}
        if await cursor.exists(self.LOG_DB, target):
            await cursor.delete(self.LOG_DB, target)

    async def write(
        self, cursor, guild_id: int, channel_id: int, username: str
    ) -> None:
        target = {
            "GuildID": guild_id, "ChannelID": channel_id
        }
        change = {"UserName": username}
        if await cursor.exists(self.DB, target):
            await cursor.update_data(self.DB, change, target)
        else:
            target.update(change)
            await cursor.insert_data(self.DB, target)

    async def delete(self, cursor, guild_id: int, channel_id: int) -> None:
        target = {"GuildID": guild_id, "ChannelID": channel_id}
        if await cursor.exists(self.DB, target):
            await cursor.delete(self.DB, target)
        else:
            raise KeyError("その設定はされていません。")

    async def read(self, cursor, guild_id: int, channel_id: int) -> tuple:
        target = dict(GuildID=guild_id, ChannelID=channel_id)
        if await cursor.exists(self.DB, target):
            return await cursor.get_data(self.DB, target)
        else:
            return ()

    async def reads(self, cursor) -> list:
        return [row async for row in cursor.get_datas(self.DB, {})]

    async def reads_by_guild_id(self, cursor, guild_id: int) -> list:
        return [
            row async for row in cursor.get_datas(
                self.DB, {"GuildID": guild_id}
            )
        ]


class Twitter(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot
        self.queue = {}
        self.cache = {}
        self.removed = []
        self.do_notification = True
        self.bot.loop.create_task(self.init_database())
        self.HEADERS = {
            "Authorization": f"Bearer {self.bot.secret['twitter']['token']}"
        }

    async def error_handle_wrapper(self, coro):
        # エラーを表示するためのラッパーです。
        # set_exception_handlerでもいいけどbot.loopにそれを設定したくないから。
        try:
            return await coro
        except Exception as e:
            print("Twitter Notification has raised error:", e)
            self.bot.loop.create_task(
                self.error_channel.send(f"Twitter has raised error:{e}")
            )

    async def init_database(self):
        # いろいろ準備をするための関数です。

        self.error_channel = self.bot.get_user(634763612535390209)

        # データベースを準備する。
        super(commands.Cog, self).__init__(
            self.bot.mysql
        )
        await self.init_table()

        # Twitterの通知ループを動かす。
        self.worker.start()
        self.notification_task = self.bot.loop.create_task(
            self.error_handle_wrapper(self.run_twitter_notification()),
            name="TwitterNotificationLoop"
        )

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
    ENDPOINT = "https://api.twitter.com/2/users/{}/tweets?max_results=5"

    async def get_user_id(self, username: str, retry: bool = False) -> str:
        # 指定されたユーザーのIDを取得する。
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
                        return user_id
            except client_exceptions.ClientOSError as e:
                if retry:
                    raise e
                else:
                    await asyncio.sleep(1)
                    return await self.get_user_id(username, True)

    async def delete_data(self, row: tuple) -> None:
        await self.delete(row[0], row[1])
        await self.delete_sended(row[1])

    async def run_twitter_notification(self) -> None:
        # Twitterの通知を行う関数です。
        while self.bot.is_ready() and self.do_notification:
            for row in await self.reads():
                if row:
                    channel = self.bot.get_channel(row[1])

                    if (channel is None
                            or not (user_id := await self.get_user_id(row[-1]))):
                        # もしチャンネルがみつからないならその設定を削除する。
                        # またはユーザーが見つからない場合でも削除する。
                        await self.delete_data(row)
                        continue
                    if channel.id in self.removed:
                        self.removed.remove(channel.id)
                        continue

                    # ユーザーのツイートを取得する。
                    async with self.bot.session.get(
                        self.ENDPOINT.format(user_id),
                        headers=self.HEADERS
                    ) as r:
                        data = await r.json(loads=loads)

                    if ("errors" in data and data["errors"]
                            and data["errors"][0]["title"] == "Not Found Error"):
                        # もしユーザーが見つからないならデータを消す。
                        await channel.send(
                            f"Error:{row[-1]}というユーザーのツイートを取得できませんでした。"
                        )
                        await self.delete_data(row)
                    elif "data" in data:
                        # 取得したツイートはキューに入れる。
                        # それを十秒毎にWorkerが送信する。
                        for data in data["data"]:
                            # キューの準備をする。
                            if channel.id not in self.queue:
                                self.queue[channel.id] = {
                                    "content": [],
                                    "length": 0,
                                    "channel": channel
                                }
                            # メッセージのURLの埋め込み表示は五つまでだから五つ登録されたら一番最初を削除する。
                            if self.queue[channel.id]["length"] == 5:
                                del self.queue[channel.id]["content"][0]
                                self.queue[channel.id]["length"] -= 1

                            # 既に通知を送信したツイートじゃなければツイート通知をする。
                            if not await self.check(channel.id, data["id"]):
                                self.queue[channel.id]["content"].append(
                                    "https://twitter.com/{}".format(
                                        f"{row[-1]}/status/{data['id']}"
                                    )
                                )
                                await self.sended(channel.id, data["id"])
                                self.queue[channel.id]["length"] += 1
                    else:
                        print("Error on Twitter:", data)

                    await asyncio.sleep(30)
            await asyncio.sleep(1)

    def cog_unload(self):
        self.worker.cancel()
        self.do_notification = False
        self.notification_task.cancel()

    @tasks.loop(seconds=10)
    async def worker(self):
        # self.run_twitter_notificationで保存されたキューにあるものを送信する。
        for key in list(self.queue.keys()):
            if self.queue[key]["content"]:
                try:
                    await self.queue[key]["channel"].webhook_send(
                        username=f'RT - Twitter Notification',
                        avatar_url="http://tasuren.syanari.com/RT/rt_icon.png",
                        content="\n".join(reversed(self.queue[key]["content"]))
                    )
                except Exception as e:
                    if self.bot.test:
                        print("RTwitter has exception error:", e)
                finally:
                    del self.queue[key]

    @commands.command(
        extras={
            "headding": {
                "ja": "Twitter通知機能", "en": "Twitter Notification"
            }, "parent": "ServerUseful"
        }
    )
    @commands.cooldown(1, 15, commands.BucketType.guild)
    @commands.has_permissions(manage_channels=True)
    async def twitter(self, ctx, *, word):
        """!lang ja
        --------
        Twitterのユーザーのツイートを通知を設定します。

        Parameters
        ----------
        word : str
            Twitterのユーザー名です。  
            (プロフィール画面にある`@`から始まる名前で`@`は名前に含めなくて良いです。)

        Examples
        --------
        `rt!twitter UN_NERV` 特務機関NERVの災害情報を通知する。

        Notes
        -----        
        設定したユーザーのツイートじゃないツイートが通知されることがありますが、それは設定したユーザーによるリツイートですので心配する必要はないです。  
        設定後の最初は既にツイートしたものが何件か送信されることがありますが気にしないでください。

        Warnings
        --------
        デフォルトでは一つのサーバーにつき三つまで設定が可能です。  
        もし要望があればプレミアム機能を作りプレミアムに加入している人のみ十設定可能にします。  
        そしてこの機能はまだベータ版ですので不具合がある可能性があります。  
        **そしてこの機能はベータです。しっかり動作しない可能性があります。**

        !lang en
        --------
        Set twitter user tweet notification to channel.

        Parameters
        ----------
        word : str
            Name of target user that you want notification.

        Examples
        --------
        `rt!twitter HumansNoContext`

        Notes
        -----
        You may get notifications of tweets by people other than the user you set up, but that's not a bug because they are retweets by the user you set up.

        Warnings
        --------
        You can set than 3 notification channel per server.  
        And this function is BETA!"""
        if word.lower() in ("off", "disable", "0", "false"):
            try:
                await self.delete(ctx.guild.id, ctx.channel.id)
            except KeyError:
                await ctx.reply(
                    {"ja": "まだ設定されていません。",
                     "en": "Twitter has not set yet."}
                )
            else:
                if ctx.channel.id not in self.removed:
                    self.removed.append(ctx.channel.id)
                await self.delete_sended(ctx.channel.id)
                await ctx.reply("Ok")
        else:
            if len(await self.reads_by_guild_id(ctx.guild.id)) == 3:
                await ctx.reply(
                    {"ja": "一つのサーバーにつき三つまで設定が可能です。",
                     "en": "You can set up to three Twitter notifications per server."}
                )
            elif await self.get_user_id(word):
                if ctx.channel.id in self.removed:
                    self.removed.remove(ctx.channel.id)
                await self.write(ctx.guild.id, ctx.channel.id, word)
                await ctx.reply("Ok")
            else:
                await ctx.reply(
                    {"ja": "そのユーザーが見つかりませんでした。",
                     "en": "The user is not found."}
                )


def setup(bot):
    bot.add_cog(Twitter(bot))
