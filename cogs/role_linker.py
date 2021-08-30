# RT - Role Linker

from discord.ext import commands
import discord

from rtlib import mysql, DatabaseLocker
from typing import Optional


class DataManager(DatabaseLocker):

    DB = "RoleLinker"

    def __init__(self, db):
        self.db = db
        self.auto_cursor = True

    async def init_table(self) -> None:
        await self.cursor.create_table(
            self.DB, {
                "GuildID": "BIGINT", "Original": "BIGINT",
                "Role": "BIGINT"
            }
        )

    async def write(
        self, guild_id: int, original_role_id: int,
        role_id: int
    ) -> None:
        target = {
            "GuildID": guild_id, "Original": original_role_id
        }
        change = dict(Role=role_id)
        if await self.cursor.exists(self.DB, target):
            await self.cursor.update_data(self.DB, change, target)
        else:
            target.update(change)
            await self.cursor.insert_data(self.DB, target)

    async def delete(self, guild_id: int, original_role_id: int) -> None:
        target = {"GuildID": guild_id, "Original": original_role_id}
        if await self.cursor.exists(self.DB, target):
            await self.cursor.delete(self.DB, target)
        else:
            raise KeyError("そのロールリンクは見つかりませんでした。")

    async def read(self, guild_id: int, original_role_id: int) -> Optional[int]:
        target = {"GuildID": guild_id, "Original": original_role_id}
        if await self.cursor.exists(self.DB, target):
            if (row := await self.cursor.get_data(self.DB, target)):
                return row[-1]
        return None

    async def get_all(self, guild_id: int) -> list:
        target = dict(GuildID=guild_id)
        if await self.cursor.exists(self.DB, target):
            return [row async for row in self.cursor.get_datas(self.DB, target)]
        else:
            return []


class RoleLinker(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        super(commands.Cog, self).__init__(
            await self.bot.mysql.get_database()
        )
        await self.init_table()

    @commands.group(
        extras={
            "headding": {
                "ja": "ロールリンカー, 役職が付与/削除された際に他も付与/削除するようにする機能",
                "en": "Role linker, Ability to grant/delete other positions when they are granted/deleted."
            }, "parent": "ServerUseful"
        }
    )
    async def linker(self, ctx):
        """!lang ja
        --------
        ロールリンカー、役職が付与/削除された際に他の役職も付与/削除するようにする機能です。  
        認証機能にて複数の役職を付与するようにしたい際に使えます。  
        `rt!linker`と実行することで登録されてるロールリンクの一覧を表示できます。

        !lang en
        --------
        Ability to grant/delete other positions when they are granted/deleted.  
        It can be use when you want set captcha role multiple.
        You can do `rt!linker` to see role link that registerd list."""
        if not ctx.invoked_subcommand:
            await ctx.reply(
                embed=discord.Embed(
                    title={
                        "ja": "ロールリンクリスト",
                        "en": "Role link list"
                    },
                    description="\n".join(
                        f"<@&{row[1]}>：<@&{row[2]}>"
                        for row in await self.get_all(
                            ctx.guild.id
                        )
                    ),
                    color=self.bot.colors["normal"]
                )
            )

    @linker.command()
    async def link(self, ctx, target: discord.Role, link_role: discord.Role):
        """!lang ja
        --------
        役職リンクを設定します。  
        10個まで登録可能です。

        Parameters
        ----------
        target : 役職のメンションまたは名前
            リンク対象の役職です。
        link_role : 役職のメンションまたは名前
            リンクする役職です。

        Examples
        --------
        `rt!link 認証済み メンバー`
        認証済みの役職がついたらメンバーという役職をつけます。

        !lang en
        --------
        Sets the job title link.
        You can register up to 10 of them.

        Parameters
        ----------
        target : Mention or name of the position
            The position to link to.
        link_role : Mention or name of the role
            The role to link to.

        Examples
        --------
        `rt!link authenticated member`.
        If the position is authenticated, it will be given the title member."""
        if len(await self.get_all(ctx.guild.id)) == 10:
            await ctx.reply(
                {"ja": "これ以上リンクすることはできません。",
                 "en": "No more links can be made."}
            )
        else:
            await self.write(ctx.guild.id, target.id, link_role.id)
            await ctx.reply("Ok")

    @linker.command()
    async def unlink(self, ctx, target: discord.Role):
        """!lang ja
        --------
        linkの逆です。  
        役職リンクを解除します。

        Parameters
        ----------
        target : 役職のメンションまたは名前
            役職リンクに設定されている役職です。

        !lang en
        --------
        The opposite of link.  
        Removes the position link.

        Parameters
        ----------
        target : Mention or name of the position
            The position set in the position link."""
        try:
            await self.delete(ctx.guild.id, target.id)
        except KeyError:
            await ctx.reply(
                {"ja": "そのロールリンクが見つかりませんでした。",
                 "en": "That role link is not found."}
            )
        else:
            await ctx.reply("Ok")

    async def role_update(
        self, mode: str, role: discord.Role,
        member: discord.Member
    ) -> None:
        link_role_id = await self.read(
            member.guild.id, role.id
        )
        if link_role_id:
            link_role = member.guild.get_role(link_role_id)
            if link_role:
                if mode == "add" and not member.get_role(link_role_id):
                    await member.add_roles(link_role)
                elif mode == "remove" and member.get_role(link_role_id):
                    await member.remove_roles(link_role)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if self.bot.is_ready():
            for role in before.roles:
                if not after.get_role(role.id):
                    # もしロールが削除されたなら。
                    await self.role_update("remove", role, after)
            for role in after.roles:
                if not before.get_role(role.id):
                    # もしロールが追加されたなら。
                    await self.role_update("add", role, after)


def setup(bot):
    bot.add_cog(RoleLinker(bot))