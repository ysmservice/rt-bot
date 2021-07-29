# RT - Database Manager

from discord.ext import commands
from ujson import loads

from data import is_admin


class DatabaseManager(commands.Cog):
    """データベース管理用コマンドをまとめたコグです。"""
    def __init__(self, bot):
        self.bot, self.rt = bot, bot.data
        self.db = self.rt["mysql"]

    @commands.Cog.listener()
    async def on_ready(self):
        # テスト用のテーブルを作る。
        async with self.db.get_cursor() as cursor:
            columns = {
                "c1": "TEXT",
                "c2": "TEXT",
                "c3": "TEXT",
                "json": "TEXT"
            }
            await cursor.create_table("test", columns)

    @commands.group(aliases=("db",))
    async def database(self, ctx):
        """databaseコマンドグループです。"""
        if not ctx.subcommand_invoked:
            await ctx.reply("使い方が間違っています。")

    @database.command()
    @is_admin()
    async def create_table(self, ctx, table, columns, ine: bool = True, commit: bool = True):
        columns = loads(columns)
        async with self.db.get_cursor() as cursor:
            await cursor.create_table(table, colunms, ine, commit)
        await ctx.reply("Ok")

    @database.command()
    @is_admin()
    async def drop_table(self, ctx, table, ie: bool = True, commit: bool = True):
        async with self.db.get_cursor() as cursor:
            await cursor.drop_table(table, ie, commit)
        await ctx.reply("Ok")

    @dabase.command()
    @is_admin()
    async def insert_data(self, ctx, table, values, commit: bool = True):
        async with self.db.get_cursor() as cursor:
            await cursor.insert_data(table, loads(values), commit)
        await ctx.reply("Ok")

    @database.command()
    @is_admin()
    async def update_data(self, ctx, table, values, targets, commit: bool = True):
        async with self.db.get_cursor() as cursor:
            await cursor.update_data(table, loads(values), loads(targets), commit)
        await ctx.reply("Ok")

    @database.command()
    @is_admin()
    async def exists(self, ctx, table, targets):
        async with self.db.get_cursor() as cursor:
            await cursor.exists(table, loads(targets))
        await ctx.reply("Ok")

    @database.command()
    @is_admin()
    async def delete(self, ctx, table, targets, commit: bool = True):
        async with self.db.get_cursor() as cursor:
            await cursor.delete(table, loads(targets), commit)
        await ctx.reply("Ok")

    @database.command()
    @is_admin()
    async def get_data(self, ctx, table, targets, fetchall: bool = True):
        async with self.db.get_cursor() as cursor:
            await cursor.get_data(table, loads(targets), fetchall)
        await ctx.reply("Ok")

    @database.command()
    @is_admin()
    async def execute(self, ctx, *, cmd):
        """`rt!dabase execute cmd` MySQLのコマンド実行します。"""
        commit, fetch = False, False
        if "--commit " in cmd:
            cmd = cmd.replace("--commit ", "")
            commit = True
        if "--fetch " in cmd:
            cmd = cmd.replace("--fetch ", "")
            fetch = True
        async with self.db.get_cursor() as cursor:
            await cursor.cursor.execute(cmd)
            if commit:
                await self.db.commit()
                rows = "..."
            if fetch:
                rows = await cursor.fetchall()
        await ctx.reply(f"Ok\n```\n{rows}\n```")


def setup(bot):
    bot.add_cog(DatabaseManager(bot))
