# RT - Original Menu Message

from discord.ext import commands
import discord

from rtlib import mysql, DatabaseManager
from rtlib.ext import componesy
from time import time


class DataManager(DatabaseManager):
    def __init__(self, db, maxsize: int = 30):
        self.db = db
        self.maxsize = maxsize

    async def init_table(self, cursor) -> None:
        await cursor.create_table(
            "originalMenu", {
                "GuildID": "BIGINT", "ChannelID": "BIGINT",
                "MessageID": "BIGINT", "Data": "JSON",
                "RegTime": "BIGINT"
            }
        )

    async def write(
            self, cursor, guild_id: int, channel_id: int,
            message_id: int, data: dict) -> None:
        await cursor.cursor.execute(
            """SELECT * FROM originalMenu
                WHERE GuildID = %s
                ORDER BY RegTime DESC;""",
            (guild_id,)
        )
        if len(rows := await cursor.cursor.fetchall()) == self.maxsize:
            # もし十個作っているなら最初に作ったやつを消す。
            await cursor.delete(
                "originalMenu", {
                    "GuildID": rows[-1][0], "ChannelID": rows[-1][1],
                    "MessageID": rows[-1][2]
                }
            )
        await cursor.insert_data(
            "originalMenu", {
                "GuildID": guild_id, "ChannelID": channel_id,
                "MessageID": message_id, "data": data,
                "RegTime": int(time())
            }
        )

    async def read(
        self, cursor, guild_id: int, channel_id: int,
        message_id: int) -> tuple:
        target = {
            "GuildID": guild_id, "ChannelID": channel_id,
            "MessageID": message_id
        }
        if await cursor.exists("originalMenu", target):
            if (row := await cursor.get_data("originalMenu", target)):
                return row
        raise KeyError("そのメニューメッセージは見つかりませんでした。")


class OriginalMenuMessage(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.on_ready())

    async def on_ready(self):
        super(commands.Cog, self).__init__(
            self.bot.mysql
        )
        await self.init_table()

    def make_embed(self, color: discord.Color, data: list) -> discord.Embed:
        return discord.Embed(
            title=data[0], description=data[1],
            color=color
        )

    CUSTOM_ID = "OriginalMenuMessage"

    @commands.command(
        aliases=["embeds", "メニュー", "めにゅー"],
        extras={
            "headding": {
                "ja": "メニューメッセージ",
                "en": "Menu message"
            }, "parent": "ServerPanel"
        }
    )
    @commands.has_permissions(manage_messages=True)
    async def menu(self, ctx: commands.Context, *, content):
        """!lang ja
        --------
        矢印ボタンで操作可能なメニューメッセージを作ります。  
        一つのサーバーにつき十個まで作成可能です。  
        **もし三十一個目を作った場合は一個目が無効になります。**

        Parameters
        ----------
        content : str
            メニュー入れる文字列です。  
            `$タイトル`のようにメニューのページのタイトルを設定して、その次の行にそのページの説明を書きます。  
            よくわからない場合は下の例を見ましょう。  
            もしメッセージに入れきれないほど書く場合はテキストファイルに書き込み、この引数を`file`としてそのテキストファイルを添付してコマンドを実行してください。

        Examples
        --------
        ```
        rt!menu $質問をする前に 1ページ目
        自分でGoogleなどである程度調べてわからない債に質問してください。
        $質問をする前に 2ページ目
        敬語を使って質問しましょう。
        $質問をする前に 3ページ目
        質問をしないように自分でできるようにしましょう。
        ```

        !lang en
        --------
        Creates a menu message that can be operated by arrow buttons.  
        Up to ten can be created per server.  
        **If you make 31, the first one will be invalid.**

        Parameters
        ----------
        content: str
            The string to menu.  
            Set the title of the page in the menu, as in `$ Title`, followed by a description of the page.  
            If you're not sure, look at the example below.

        Examples
        --------
        ```
        rt!menu $Before asking questions, page one.
        Ask yourself questions about bonds that you don't know by doing some research on Google.
        $Before I ask you a question, page two.
        Let's ask questions using honorific expressions.
        $Before I ask you a question, page three.
        Try not to ask questions and do it yourself.
        ```"""
        if content == "file":
            if ctx.message.attachments:
                at = ctx.message.attachments[0]
                if at.filename.endswith(".txt") and at.size <= 12000:
                    content = (await at.read()).decode()
                else:
                    return await ctx.reply(
                        {"ja": "ファイル形式は`txt`にしてください。",
                         "en": "The file type must be `txt`."}
                    )
            else:
                return await ctx.reply(
                    {"ja": "ファイルがアップロードされていません。",
                     "en": "The file has not been uploaded."}
                )
        page, data = 0, {}
        for content in content.split("$"):
            if content:
                page += 1
                data[str(page)] = [
                    content[:(index := content.find("\n"))],
                    content[index:]
                ]
        view = componesy.View("MenuView")
        view.add_item(
            "Button", None, emoji="◀️",
            custom_id=f"{self.CUSTOM_ID}Left"
        )
        view.add_item(
            "Button", None, emoji="▶️",
            custom_id=f"{self.CUSTOM_ID}Right"
        )
        if data:
            message = await ctx.send(
                content="1", embed=self.make_embed(ctx.author.color, data["1"]),
                view=view.get_view()
            )
            await self.write(
                ctx.guild.id, ctx.channel.id, message.id, data
            )
        else:
            await ctx.reply(
                {"ja": "内容がないので作れません。",
                 "en": "I can't make message because content is nothing."}
            )

    async def on_button_pushed(self, mode, interaction):
        try:
            row = await self.read(
                interaction.guild.id, interaction.channel.id,
                interaction.message.id
            )
        except KeyError:
            pass
        else:
            plus = -1 if mode == "left" else 1
            data = row[3].get(
                index := str(int(interaction.message.content) + plus)
            )
            if data:
                await interaction.message.edit(
                    content=index, embed=self.make_embed(
                        interaction.message.embeds[0].color, data
                    )
                )
            try:
                await interaction.response.defer()
            except Exception as e:
                self.ignored_error = e
                if self.bot.test:
                    print("Error on original menu message:", e)

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if ((custom_id := interaction.data.get("custom_id", ""))
                .startswith(self.CUSTOM_ID)):
            await self.on_button_pushed(
                custom_id.replace(self.CUSTOM_ID, "").lower(),
                interaction
            )


def setup(bot):
    bot.add_cog(OriginalMenuMessage(bot))
