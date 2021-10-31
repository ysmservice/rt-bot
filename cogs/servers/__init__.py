# RT - Servers

from typing import TYPE_CHECKING

from discord.ext import commands

from .views import ServerList
from .server import Server

if TYPE_CHECKING:
    from aiomysql import Pool
    from rtlib import Backend


class Servers(commands.Cog, Server):
    def __init__(self, bot):
        self.bot: "Backend" = bot
        self.pool: "Pool" = self.bot.mysql.pool
        self.bot.loop.create_task(self.init_table(self.pool))

    @commands.group(
        aliases=["ss", "サーバー掲示板", "サーバーズ"],
        slash_command=True
    )
    async def servers(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.reply(
                {"ja": "使用方法が違います。",
                 "en": "It is used in different ways."}
            )

    @servers.command(aliases=["reg", "add", "登録"])
    @commands.has_permissions(administrator=True)
    async def register(self, ctx, tags, *, description):
        try:
            self.make_guild(
                self, ctx.guild, description, tags.split(","),
                await ctx.channel.create_invite(
                    reason="サーバー掲示板に登録のため。"
                ), {}
            )
        except AssertionError:
            await ctx.reply(
                {"ja": "既に登録されています。",
                 "en": "It has already been registered."}
            )
        else:
            await ctx.reply("登録しました。")

    @servers.command(aliases=["解除", "unreg"])
    @commands.has_permissions(administrator=True)
    async def unregister(self, ctx):
        try:
            await self.delete_guild(self, ctx.guild.id)
        except AssertionError:
            await ctx.reply(
                {"ja": "このサーバーは登録されていません。",
                 "en": "It has not registered yet."}
            )
        else:
            await ctx.reply("登録解除しました。")

    @servers.command("list")
    async def list_(self, ctx):
        servers = await self.getall(
            self, """ORDER BY RaiseTime DESC
            LIMIT 20
            WHERE RaiseTime;"""
        )
        view = ServerList(self, servers)

    @servers.group(aliases=["更新"])
    @commands.cooldown(10, 1, commands.BucketType.guild)
    async def update(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.reply(
                {"ja": "使用方法が違います。",
                 "en": "It is used in different ways."}
            )

    async def _update(self, ctx: commands.Context, **kwargs) -> None:
        await ctx.trigger_typing()
        try:
            server: Server = self.from_guild(self, ctx.guild)
        except AssertionError:
            await ctx.reply(
                {"ja": "まだこのサーバーはサーバー掲示板に登録されていません。",
                 "en": "This server has not yet been registered on the server board."}
            )
        else:
            await server.update_data(**kwargs)
            await ctx.reply(
                {"ja": "情報を更新しました。",
                 "en": "Updated!"}
            )

    @update.command(aliases=["detail", "desc", "d", "説明欄"])
    @commands.has_permissions(administrator=True)
    async def description(self, ctx, *, description):
        await self._update(ctx, description=description)

    @update.command(aliases=["招待"])
    @commands.has_permissions(administrator=True)
    async def invite(self, ctx):
        await self._update(
            ctx, invite=await ctx.channel.create_invite(
                reason="サーバー掲示板で使う招待の更新のため。"
            )
        )

    @update.command(aliases=["タグ"])
    async def tags(self, ctx, *, tags):
        await self._update(ctx, tags=tags.split(","))


def setup(bot):
    bot.add_cog(Servers(bot))