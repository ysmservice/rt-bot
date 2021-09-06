# RT - Bump

from discord.ext import commands, tasks
import discord

from typing import Any

from rtutil.SettingAPI import SettingData, ListBox, utils
from rtlib import DatabaseManager, mysql
from asyncio import sleep
from ujson import loads
from time import time


class DataManager(DatabaseManager):
    def __init__(self, db):
        self.db = db

    async def init_table(self, cursor) -> None:
        await cursor.create_table(
            "bump", {
                "GuildID": "BIGINT", "Mode": "TEXT",
                "Data": "TEXT"
            }
        )
        await cursor.create_table(
            "bumpRanking", {
                "UserID": "BIGINT", "Mode": "TEXT", "Count": "INTEGER"
            }
        )

    async def save(self, cursor, guild_id: int, mode: str, data: dict) -> None:
        target = {"GuildID": guild_id, "Mode": mode}
        if await cursor.exists("bump", target):
            await cursor.delete("bump", target)
        target["data"] = data
        await cursor.insert_data("bump", target)

    async def load(self, cursor, guild_id: int, mode: str) -> list:
        target = {"GuildID": guild_id, "Mode": mode}
        if await cursor.exists("bump", target):
            return await cursor.get_data("bump", target)
        else:
            return [guild_id, mode, {"onoff": True}]

    async def save_ranking(self, cursor, user_id: int, mode: str, count: int) -> None:
        target = {"UserID": user_id, "Mode": mode}
        change = {"Count": count}
        if await cursor.exists("bumpRanking", target):
            await cursor.update_data("bumpRanking", change, target)
        else:
            target.update(change)
            await cursor.insert_data("bumpRanking", target)

    async def load_ranking(self, cursor, user_id: int, mode: str) -> int:
        target = {"UserID": user_id, "Mode": mode}
        if await cursor.exists("bumpRanking", target):
            if (row := await cursor.get_data("bumpRanking", target)):
                return row[-1]
            else:
                return 0
        else:
            return 0

    async def execute(self, cursor, cmd: str, args: tuple, fetch: bool = True) -> Any:
        await cursor.cursor.execute(cmd, args)
        if fetch:
            return await cursor.cursor.fetchall()


def get_extras(mode: str, callback) -> dict:
    return {
        "headding": {
            "ja": f"{mode}の通知のON/OFFをします。",
            "en": f"Change {mode} notification on/off."
        },
        "parent": "ServerTool",
        "setting": SettingData(
            "guild", {
                "ja": f"{mode}の通知のON/OFFをします。",
                "en": f"Change {mode} notification on/off"
            }, callback,
            ListBox(mode, {
                "ja": f"{mode}通知をするかどうかです。役職名を選択すれば役職メンションをして通知をします。",
                "en": "Whether to do notification or not. If you select role name, RT do mention when do notification."
            }, 0, ["..."]),
            permissions=["administrator"]
        )
    }


class Bump(commands.Cog, DataManager):

    IDS = {
        302050872383242240: {
            "mode": "bump",
            "description": ["表示順をアップしたよ", "Bump done", "Bumpeado"],
            "time": 7200
        },
        761562078095867916: {
            "mode": "up",
            "description": ["dissoku"],
            "time": 3600
        },
        716496407212589087: {
            "mode": "bump",
            "description": ["表示順をアップしたよ", "Bump done", "Bumpeado"],
            "time": 5
        },
        716496407212589087: {
            "mode": "up",
            "description": ["dissoku"],
            "time": 5
        }
    }
    BUMP_COLOR = 0x00a3af
    UP_COLOR = 0x95859c
    EMOJIS = {
        "1": "<:No1:795849530448805919>",
        "2": "<:No2:795849531774205994>",
        "3": "<:No3:795849531840397323>"
    }

    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.on_ready())

    async def on_ready(self):
        super(commands.Cog, self).__init__(
            self.bot.mysql
        )
        await self.init_table()
        self.notification.start()

    async def callback(self, ctx, item):
        if getattr(ctx, "mode", "write") == "read":
            data = await self.load(ctx.guild.id, item.name)
            onoff = "on" if data else "off"
            if onoff == "on" and data[-1].get("role"):
                onoff = ctx.guild.get_role(data[-1]["role"])
            item = utils.make_list(
                item.name, {
                    "ja": f"{item.name}通知をするかどうかです。役職名を選択すれば役職メンションをして通知をします。",
                    "en": "Whether to do notification or not. If you select role name, RT do mention when do notification."
                },
                ["on", "off"] + ctx.guild.roles, "name", onoff
            )
            return item
        else:
            role = item.texts[item.index]
            row = await self.load(ctx.guild.id, item.name)
            if role == "off":
                await self.save(ctx.guild.id, item.name, {"onoff": False})
            else:
                new = row[-1]
                if role != "on":
                    role = getattr(
                        discord.utils.get(ctx.guild.roles, name=role),
                        "id", 0
                    )
                new.update({
                    "role": role, "onoff": True
                })
                await self.save(ctx.guild.id, item.name, new)

    @commands.command(extras=get_extras("bump", callback))
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def bump(self, ctx, onoff: bool, *, role: discord.Role = None):
        """!lang ja
        --------
        Bump通知のOnOffコマンドです。

        Parameters
        ----------
        onoff : bool
            on/offです。
        role : 役職名またはメンション, optional
            通知する際にメンションする役職です。  
            オプションで選択しなくても大丈夫です。

        Examples
        --------
        `rt!bump on Bump係`

        Notes
        -----
        この機能はデフォルトでonです。

        !lang en
        --------
        Bump notification on/off command.

        Parameters
        ----------
        onoff : bool
            This is on or off.
        role : Role name or mention, optional
            Mention of role when do notification.  
            This is a option.

        Examples
        --------
        `rt!bump on BumpMan`

        Notes
        -----
        Bump notification is enable by default."""
        if role:
            texts = [role.name]
        else:
            texts = ["on" if onoff else "off"]
        await self.callback(ctx, ListBox("bump", "...", 0, texts))
        await ctx.reply("Ok", replace_language=True)

    @commands.command(extras=get_extras("up", callback))
    @commands.has_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def up(self, ctx, onoff: bool, *, role: discord.Role = None):
        if role:
            texts = [role.name]
        else:
            texts = ["on" if onoff else "off"]
        await self.callback(ctx, ListBox("up", "...", 0, texts))
        await ctx.reply("Ok", replace_language=True)

    up.__doc__ = bump.__doc__.replace("bump", "up").replace("Bump", "Up")

    async def make_ranking(self, user_id: int, mode: str) -> discord.Embed:
        rows = await self.execute(
            """SELECT * FROM bumpRanking
                WHERE Mode = %s
                ORDER BY Count DESC
                LIMIT 5""", (mode,)
        )
        now = await self.load_ranking(user_id, mode)

        # ランキングのEmbedを作る。
        embed = discord.Embed(
            title=f"{mode} ランキング / Ranking",
            description={
                "ja": f"あなたの{mode}回数は{now}です。",
                "en": f"Your {mode} count is {now}."
            },
            color=self.BUMP_COLOR if mode == "bump" else self.UP_COLOR
        )
        i = 0
        embed.add_field(
            name="‌\n",
            value="\n".join((
                f"{self.EMOJIS.get(str_i := str(i := i + 1), str_i)} "
                f"{(name := getattr(self.bot.get_user(row[0]), 'name', 'ユーザー不明'))}"
                f"：{row[-1]}") for row in rows
            )
        )

        del i, str_i
        return embed

    @commands.command(
        extras={
            "headding": {
                "ja": "Up ランキング",
                "en": "Up ranking"
            }, "parent": "Individual"
        }, name="uppers", aliases=["ur", "uprank", "あっぷらんく"]
    )
    @commands.cooldown(1, 4, commands.BucketType.user)
    async def up_ranking(self, ctx):
        """!lang ja
        --------
        DissokuのUpのランキングです。

        Aliases
        -------
        ur, uprank, あっぷらんく

        !lang en
        --------
        Show you Dissoku Up ranking.

        Aliases
        -------
        ur, uprank"""
        await self.bump_ranking(ctx, mode="up")

    def cog_unload(self):
        self.notification.cancel()

    async def get_all(self, mode: str) -> tuple:
        return await self.execute(
            "SELECT * FROM bump WHERE Mode = %s",
            (mode,)
        )

    @tasks.loop(seconds=30)
    async def notification(self):
        now = time()
        for key in self.IDS:
            mode = self.IDS[key]["mode"]
            for row in await self.get_all(mode):
                row = list(row)
                try:
                    row[-1] = loads(row[-1])
                except Exception as e:
                    if self.bot.test:
                        print("Error on bump:", e)
                else:
                    if "notification" in row[-1]:
                        if (row[-1]["notification"] <= now
                            and row[-1]["notification"] != 0):
                            # もし通知時刻になっているなら通知をする。
                            channel = self.bot.get_channel(
                                int(row[-1]["channel"])
                            )
                            if channel:
                                role = channel.guild.get_role(row[-1].get("role", 0))
                                mention = f"{role.mention}, " if role else ""
                                try:
                                    await channel.send(
                                        f"{mention}{mode}の時間だよ！ / It's time to {mode}!"
                                    )
                                except Exception as e:
                                    if self.bot.test:
                                        print("Error on bump2:", e)

                                # 通知時刻をまた通知しないようにゼロにする。
                                row[-1]["notification"] = 0
                                await self.save(channel.guild.id, mode, row[-1])

    async def delay_on_message(self, seconds: int, message: discord.Message) -> None:
        # 遅れて再取得してもう一回on_messageを実行する。
        await sleep(seconds)
        message = await message.channel.fetch_message(message.id)
        await self.on_message(message, True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message, retry: bool = False):
        if not self.bot.is_ready():
            return

        data = self.IDS.get(message.author.id)
        if (not retry and data and data["mode"] != "bump"
                and message.type == discord.MessageType.application_command):
            # もしDissokuなら数秒後に再取得してもう一度この関数on_messageを呼び出す。
            self.bot.loop.create_task(self.delay_on_message(3, message))
            return
        if not message.guild or not data or not message.embeds:
            return

        desc = message.embeds[0].description
        check = ((desc and any(
                    word in message.embeds[0].description
                    for word in data["description"]))
                if data["mode"] == "bump"
                else (message.embeds[0].fields
                    and "をアップしたよ" in message.embeds[0].fields[0].name))

        if check:
            row = await self.load(message.guild.id, data["mode"])
            if row[-1]["onoff"]:
                # 既に書き込まれてるデータに次通知する時間とチャンネルを書き込む。
                new = row[-1]
                new["notification"] = time() + data["time"]
                new["channel"] = message.channel.id
                await self.save(message.guild.id, data["mode"], new)

                # bump/up実行者を取得して回数を一上げる。
                user_id = int(
                    desc[
                        2:
                        desc.find("," if data["mode"] == "bump" else "\n") - 1
                    ]
                )
                count = await self.load_ranking(user_id, data["mode"])
                await self.save_ranking(user_id, data["mode"], count + 1)

                # 通知の設定をしたとメッセージを送る。
                await message.channel.send(
                    {"ja": f"{data['mode']}通知の設定をしました。",
                     "en": "I have set a notification schedule."},
                    target=user_id
                )


def setup(bot):
    bot.add_cog(Bump(bot))
