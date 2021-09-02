# RT - Tenki

from discord.ext import commands, easy, tasks
import discord

from rtlib import mysql, DatabaseLocker
from datetime import datetime
from asyncio import sleep
from ujson import loads
from copy import copy


with open("data/area_code.json", "r") as f:
    AREA_CODE = loads(f.read())


class DataManager(DatabaseLocker):

    DB = "TenkiData"

    def __init__(self, db):
        self.db = db
        self.auto_cursor = True

    async def init_table(self) -> None:
        await self.cursor.create_table(
            self.DB, {
                "UserID": "BIGINT", "Code": "TEXT",
                "NofTime": "TEXT"
            }
        )

    async def write(self, user_id: int, code: str, nof_time: str) -> None:
        target = {"UserID": user_id}
        change = {"Code": code, "NofTime": nof_time}
        if await self.cursor.exists(self.DB, target):
            await self.cursor.update_data(self.DB, change, target)
        else:
            target.update(change)
            await self.cursor.insert_data(self.DB, target)

    async def delete(self, user_id: int) -> None:
        target = {"UserID": user_id}
        if await self.cursor.exists(self.DB, target):
            await self.cursor.delete(self.DB, target)
        else:
            raise KeyError("そのユーザーは設定していません。")

    async def reads(self) -> list:
        return [row async for row in self.cursor.get_datas(self.DB, {})]

i = -1
PREFECTURES = [(data["@title"], i)
               for data in AREA_CODE["pref"]
               if (i := i + 1) or True]


class Tenki(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot
        self.tenki_notification.start()

        self.view = easy.View("TenkiPrefectureSelect")
        add_item = lambda options, true_count: self.view.add_item(
            "Select", self.on_select_prefecture,
            options=options,
            placeholder=f"都道府県 {true_count}",
            custom_id="tenkiShowPrefecture%s" % true_count
        )
        count, options, true_count = 0, [], 0
        for name, value in PREFECTURES:
            count += 1
            if count == 25:
                add_item(options, (true_count := true_count + 1))
                count, options = 0, []
            else:
                options.append(
                    discord.SelectOption(
                        label=name, value=value
                    )
                )
        if count != 24:
            add_item(options, true_count + 1)

        self.bot.loop.create_task(self.on_ready())

    async def on_ready(self):
        await self.bot.wait_until_ready()
        super(commands.Cog, self).__init__(
            await self.bot.mysql.get_database()
        )
        await self.init_table()

    @commands.command(
        slash_command=True, aliases=["天気"],
        description="日本の天気を表示します。",
        extras={
            "headding": {
                "ja": "天気予報を表示、通知します。",
                "en": "Japan Forecast"
            }, "parent": "Individual"
        }
    )
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def tenki(self, ctx):
        """!lang ja
        --------
        コマンドを実行した後に選択された天気を表示します。  
        またこのコマンドを使って天気を表示した後に指定した時刻に毎日天気通知を送ることもできます。  
        もし設定した天気通知をオフにしたい場合は`rt!tenkiset off`と実行してください。

        !lang en
        --------
        Sorry, This command is not supported English yet.  
        But, you can run this command."""
        await ctx.reply("都道府県を選んでください。", view=self.view())

    async def make_embed(self, code: str) -> discord.Embed:
        # 天気予報を取得してEmbedを作る。
        async with self.bot.session.get(
            f"https://weather.tsukumijima.net/api/forecast/city/{code}"
        ) as r:
            data = loads(await r.read())

        embed = discord.Embed(
            title=data["title"],
            color=0x1e92d9,
            url=data["link"]
        )
        embed.set_footer(
            text=data["copyright"]["title"],
            icon_url=data["copyright"]["image"]["url"]
        )
        if data["forecasts"]:
            forecast = data["forecasts"][0]
            embed.add_field(
                name=f"‌\n{forecast['dateLabel']} - {forecast['telop']}",
                value=forecast["detail"]["weather"], inline=False
            )
            embed.set_thumbnail(url=forecast["image"]["url"])
        embed.add_field(
            name="詳細", value=data["description"]["text"],
            inline=False
        )

        return embed

    async def on_select_prefecture(self, select, interaction):
        if select.values:

            if select.custom_id.startswith("tenkiShowPrefecture"):
                # 都道府県選択されたら。
                i = -1
                view = easy.View("TenkiShowCity")
                view.add_item(
                    "Select", self.on_select_prefecture, options = [
                        discord.SelectOption(
                            label=data["@title"], value=f"{select.values[0]} {i}"
                        )
                        for data in AREA_CODE["pref"][int(select.values[0])]["city"]
                        if (i := i + 1) or True
                    ],
                    placeholder="市町村", custom_id="tenkiShowCity"
                )
                kwargs = {"content": "市町村を選んでください。", "view": view()}

            elif select.custom_id == "tenkiShowCity":
                # 市町村を指定されたら天気を取得してEmbedにして送信する。
                p, c = list(map(int, select.values[0].split()))

                view = easy.View("TenkiNotification")
                view.add_item(
                    "Select", self.on_set_notification,
                    options=[
                        discord.SelectOption(
                            label=(value := f"{str(i).zfill(2)}:00"),
                            value=value
                        )
                        for i in range(24)
                    ], placeholder="天気通知を設定する。"
                )

                kwargs = {
                    "embed": await self.make_embed(
                        AREA_CODE["pref"][p]["city"][c]["@id"]
                    ), "view": view(),
                    "content": AREA_CODE["pref"][p]["city"][c]["@id"]
                }
            else:
                return

            await interaction.response.edit_message(**kwargs)

    async def on_set_notification(self, select, interaction):
        # tenkiコマンド実行後に通知を設定されたら。
        if select.values:
            ctx = await self.bot.get_context(interaction.message)
            ctx.message.author = interaction.user
            await self.tenkiset(
                ctx, interaction.message.content, select.values[0]
            )

    @commands.command()
    async def tenkiset(self, ctx, code, time=None):
        if code.lower() in ("off", "0", "disable", "false"):
            try:
                await self.delete(ctx.author.id)
            except KeyError:
                await ctx.reply("あなたはまだ設定していません。")
            else:
                await ctx.reply("Ok")
        elif time:
            await self.write(ctx.author.id, code, time)
            await ctx.reply("Ok")
        else:
            await ctx.reply("引数が正しくありません。")

    @tasks.loop(minutes=1)
    async def tenki_notification(self):
        # 天気通知を送るループです。
        if not self.bot.is_ready():
            await self.bot.wait_until_ready()
            await sleep(3)

        now = datetime.now().strftime('%H:%M')
        for row in await self.reads():
            if row and row[2] == now:
                user = self.bot.get_user(row[0])
                if user:
                    embed = await self.make_embed(row[1])
                    try:
                        await user.send(embed=embed)
                    except Exception as e:
                        print("Error on tenki's notification", e)
                else:
                    await self.delete(row[0])

    def cog_unload(self):
        self.tenki_notification.cancel()


def setup(bot):
    bot.add_cog(Tenki(bot))