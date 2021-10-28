# RT - Role Linker

from discord.ext import commands
import discord

from rtlib import mysql, DatabaseManager
from typing import Optional


class DataManager(DatabaseManager):

    DB = "RoleLinker"

    def __init__(self, db):
        self.db = db

    async def init_table(self, cursor) -> None:
        await cursor.create_table(
            self.DB, {
                "GuildID": "BIGINT", "Original": "BIGINT",
                "Role": "BIGINT", "Reverse": "TINYINT"
            }
        )

    async def write(
        self, cursor, guild_id: int, original_role_id: int,
        role_id: int, reverse: bool = False
    ) -> None:
        target = {
            "GuildID": guild_id, "Original": original_role_id
        }
        if reverse and await cursor.exists(self.DB, {"Original": role_id}):
            raise ValueError("既に設定されているのでその役職で設定できません。")
        change = dict(Role=role_id, Reverse=int(reverse))
        if await cursor.exists(self.DB, target):
            await cursor.update_data(self.DB, change, target)
        else:
            target.update(change)
            await cursor.insert_data(self.DB, target)

    async def delete(self, cursor, guild_id: int, original_role_id: int) -> None:
        target = {"GuildID": guild_id, "Original": original_role_id}
        if await cursor.exists(self.DB, target):
            await cursor.delete(self.DB, target)
        else:
            raise KeyError("そのロールリンクは見つかりませんでした。")

    async def read(self, cursor, guild_id: int, original_role_id: int) -> Optional[int]:
        target = {"GuildID": guild_id, "Original": original_role_id}
        if await cursor.exists(self.DB, target):
            if (row := await cursor.get_data(self.DB, target)):
                return row[-2], row[-1]
        return None

    async def get_all(self, cursor, guild_id: int) -> list:
        target = dict(GuildID=guild_id)
        if await cursor.exists(self.DB, target):
            return [row async for row in cursor.get_datas(self.DB, target)]
        else:
            return []


class RoleLinker(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.on_ready())

    async def on_ready(self):
        super(commands.Cog, self).__init__(
            self.bot.mysql
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
    async def link(self, ctx, target: discord.Role, link_role: discord.Role, reverse: bool = False):
        """!lang ja
        --------
        役職リンクを設定します。  
        15個まで登録可能です。

        Parameters
        ----------
        target : 役職のメンションまたは名前
            リンク対象の役職です。
        link_role : 役職のメンションまたは名前
            リンクする役職です。
        reverse : bool, default off
            役職が付与されたら指定したlink_roleを剥奪するのように通常の逆にするかどうかです。  
            onまたはoffを入れます。

        Examples
        --------
        `rt!linker link 認証済み メンバー`
        認証済みの役職がついたらメンバーという役職をつけます。

        Notes
        -----
        reverseをonにする場合は対象の役職を既にロールリンカーに登録されている役職に設定することはできません。  
        理由はこうしなければループを作ることが可能になりRTを妨害できてしまうからです。ご了承ください。

        !lang en
        --------
        Sets the job title link.
        You can register up to 10 of them.

        Parameters
        ----------
        target : Mention or name of the position
            The role that triggers the grant or drop of the role.
        link_role : Mention or name of the role
            The role to be granted or removed when target is granted or removed.
        reverse : bool, default off
            Whether or not to reverse the normal behavior, such as stripping the specified link_role when a role is granted.  
            Can be on or off.

        Examples
        --------
        `rt!linker link authenticated member`.
        If the role is authenticated, it will be given the role "member".

        Notes
        -----
        If reverse is on, you cannot set the target role to a role that is already registered with the role linker.  
        The reason is that if you don't do this, you can create loops and interfere with RT. Thank you for your understanding."""
        if len(await self.get_all(ctx.guild.id)) == 15:
            await ctx.reply(
                {"ja": "これ以上リンクすることはできません。",
                 "en": "No more links can be made."}
            )
        else:
            try:
                await self.write(
                    ctx.guild.id, target.id, link_role.id, reverse
                )
            except ValueError:
                await ctx.reply(
                    {"ja": "既にロールリンカーに登録されている役職を設定することはできません。",
                     "en": "You can't set the target role to a role that is already registered."}
                )
            else:
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
        row = await self.read(
            member.guild.id, role.id
        )
        if row:
            link_role = member.guild.get_role(row[0])
            if link_role:
                role, coro = member.get_role(row[0]), None
                if mode == "add":
                    if not row[1] and not role:
                        coro = member.add_roles(link_role)
                    elif row[1] and role:
                        coro = member.remove_roles(link_role)
                elif mode == "remove":
                    if not row[1] and role:
                        coro = member.remove_roles(link_role)
                    elif row[1] and not role:
                        coro = member.add_roles(link_role)

                if coro:
                    await coro

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if self.bot.is_ready():
            for role in before.roles:
                if not after.get_role(role.id):
                    # もしロールが削除されたなら。
                    self.bot.dispatch("role_remove", role, after)
                    await self.role_update("remove", role, after)
            for role in after.roles:
                if not before.get_role(role.id):
                    # もしロールが追加されたなら。
                    self.bot.dispatch("role_add", role, after)
                    await self.role_update("add", role, after)


def setup(bot):
    bot.add_cog(RoleLinker(bot))
