# RT - Ng Nickname

from discord.ext import commands
import discord

from aiomysql import Pool


class NGNickName(commands.Cog):

    DB = "NgNickName"

    def __init__(self, bot):
        self.bot = bot
        self.pool: Pool = self.bot.mysql.pool
        self.bot.loop.create_task(self.init_database())

    async def init_database(self):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""CREATE TABLE IF NOT EXISTS {self.DB}(
                        GuildID BIGINT NOT NULL PRIMARY KEY, Word TEXT
                    );"""
                )

    async def getall(self, guild_id: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""SELECT Word FROM {self.DB}
                    WHERE GuildID = %s;""",
                    (guild_id,)
                )
                return [row[0] for row in await cursor.fetchall() if row]

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick is None:
            before.nick = ""
        if after.nick:
            if before.nick != after.nick:
                for word in await self.getall(after.guild.id):
                    if word in after.nick:
                        try:
                            await after.edit(nick=before.nick, reason="NGニックネームにひっかかったため。")
                        except discord.Forbidden:
                            pass
                        else:
                            await after.send(
                                "<:error:878914351338246165> あなたのそのニックネームは" \
                                f"`{after.guild.name}`で有効ではありません。\n" \
                                "お手数ですが別のものにしてください。\n" \
                                f"検知した禁止ワード：`{word}`"
                            )
                        finally:
                            break

    @commands.group(
        aliases=["NGニックネーム", "nn"], extras={
            "headding": {
                "ja": "NGニックネーム", "en": "NG Nickname"
            }, "parent": "ServerSafety"
        }
    )
    async def ngnick(self, ctx):
        """!lang ja
        -------
        ニックネームに含められないNGニックネームを設定します。  
        `rt!ngnick`で現在登録しているNGニックネームの一覧を表示します。

        Aliases
        -------
        NGニックネーム, nn

        Notes
        -----
        サーバーのオーナーのニックネームは、RTに管理者権限があっても更新は権限の仕様上できません。

        !lang en
        --------
        Sets the NG nicknames that cannot be included in nicknames.  
        Displays the list of NG nicknames currently registered with `rt!ngnick`.

        Aliases
        -------
        nn"""
        if not ctx.invoked_subcommand:
            await ctx.reply(
                embed=discord.Embed(
                    title="NGニックネームリスト",
                    description=(
                        "`" + "`, `".join(words) + "`"
                        if (words := await self.getall(ctx.guild.id))
                        else "まだありません。"
                    ), color=self.bot.colors["normal"]
                )
            )

    @ngnick.command(aliases=["追加"])
    async def add(self, ctx, *, word):
        """!lang ja
        --------
        NGニックネームを追加します。

        Parameters
        ----------
        word : str
            追加するNGニックネームです。

        Examples
        --------
        `rt!ngnick add tasuren`  
        tasurenが本当のサーバーのオーナーなのでこれは禁止します。

        Aliases
        -------
        追加

        !lang en
        --------
        Add NG Nickname.

        Parameters
        ----------
        word : str
            The NG nickname to add.

        Examples
        --------
        `rt!ngnick add tasuren`.  
        This is banned because tasuren is the real owner of the server."""
        await ctx.trigger_typing()

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""INSERT INTO {self.DB} (GuildID, Word) VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE Word = %s;""",
                    (ctx.guild.id, word, word)
                )

        # 既にニックネームにwordが入ってる人は訂正する。
        for member in ctx.guild.members:
            if member.nick and word in member.nick:
                await member.edit(nick=member.name)

        await ctx.reply(
            {"ja": "追加しました。",
             "en": "Added."}
        )

    @ngnick.command(aliases=["削除"])
    async def remove(self, ctx, *, word):
        """!lang ja
        --------
        NGニックネームを削除します。

        Parameters
        ----------
        word : str
            削除するNGニックネームです。

        Aliases
        -------
        削除

        !lang en
        --------
        Remove NG Nickname.

        Parameters
        ----------
        word : str
            Target NG Nickname."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""DELETE FROM {self.DB}
                    WHERE GuildID = %s;""",
                    (ctx.guild.id,)
                )
        await ctx.reply(
            {"ja": "削除しました。",
             "en": "Removed."}
        )


def setup(bot):
    bot.add_cog(NGNickName(bot))