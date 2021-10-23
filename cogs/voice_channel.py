# RT - Voice Channel

from typing import TYPE_CHECKING, Optional, Union, Literal, Tuple, List

from discord.ext import commands
import discord

if TYPE_CHECKING:
    from rtlib import Backend
    from aiomysql import Pool


class DataManager:

    TABLE = "VCChannel"

    def __init__(self, cog: "VCChannel"):
        self.cog = cog
        self.pool: "Pool" = self.cog.bot.mysql.pool
        self.cog.bot.loop.create_task(self.init_table())

    async def init_table(self) -> None:
        """テーブルを準備します。インスタンス化した際に自動で実行されます。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""CREATE TABLE IF NOT EXISTS {self.TABLE} (
                        GuildID BIGINT, ChannelID BIGINT, Mode TEXT,
                        Role BIGINT, Template TEXT
                    );"""
                )

    async def write(
        self, guild_id: int, channel_id: int, mode: str,
        role_id: int, template: str
    ) -> None:
        """設定を書き込みます。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT ChannelID FROM {self.TABLE} WHERE GuildID = %s;",
                    (guild_id,)
                )
                assert len(await cursor.fetchall()) <= 50, "50より多く設定することはできません。"
                await cursor.execute(
                    f"""SELECT ChannelID FROM {self.TABLE}
                        WHERE ChannelID = %s AND Mode = %s;""",
                    (channel_id, mode)
                )
                if await cursor.fetchone():
                    await cursor.execute(
                        f"""UPDATE {self.TABLE} SET Role = %s, Template = %s
                        WHERE GuildID = %s AND ChannelID = %s AND Mode = %s;""",
                        (role_id, template, guild_id, channel_id, mode)
                    )
                else:
                    await cursor.execute(
                        f"""INSERT INTO {self.TABLE} VALUES (%s, %s, %s, %s, %s);""",
                        (guild_id, channel_id, mode, role_id, template)
                    )

    async def read(self, channel_id: int
    ) -> Optional[List[Tuple[Literal["tc", "vc"], int, str]]]:
        """設定を読み込みます。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"""SELECT Mode, Role, Template FROM {self.TABLE}
                    WHERE ChannelID = %s;""", (channel_id,)
                )
                if (rows := await cursor.fetchall()):
                    return [(row[0], row[1], row[2]) for row in rows if row]

    async def delete(self, channel_id: int, mode: str) -> None:
        """設定を削除します。"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT ChannelID FROM {self.TABLE} WHERE ChannelID = %s;",
                    (channel_id, mode)
                )
                assert await cursor.fetchone(), "その設定が見つかりませんでした。"
                await cursor.execute(
                    f"DELETE FROM {self.TABLE} WHERE ChannelID = %s AND Mode = %s;",
                    (channel_id, mode)
                )


class VCChannel(commands.Cog, DataManager):
    def __init__(self, bot):
        self.bot: "Backend" = bot
        super(commands.Cog, self).__init__(self)

    @commands.command(aliases=["vcチャンネル", "ボイスチャンネル"])
    async def vcc(
        self, ctx: commands.Context,
        channel: Union[discord.VoiceChannel, discord.StageChannel, discord.Object],
        mode: Literal["tc", "vc"], role: Union[discord.Role, Literal["null"]], *,
        template: Union[bool, str] = "!name!'s vc"
    ):
        await ctx.trigger_typing()
        if isinstance(template, bool) and not template:
            try:
                await self.delete(channel.id, mode)
            except AssertionError:
                await ctx.reply(
                    {"ja": f"<#{channel.id}>は設定されていません。",
                     "en": f"<#{channel.id}> is not set."}
                )
            else:
                await ctx.reply(
                    {"ja": "VCチャンネルの設定を削除しました。",
                     "en": "Removed setting the vc channel."}
                )
        else:
            await self.write(ctx.guild.id, ctx.channel.id, mode, role.id, template)
            await ctx.reply(
                {"ja": f"vcチャンネルとして<#{channel.id}>を設定しました。",
                "en": f"I set <#{channel.id}> as VC Channel."}
            )

    async def on_update(
        self, mode: str, member: discord.Member, vc: discord.VoiceState
    ) -> None:
        if (row := await self.read(vc.id)):
            if mode == "join":
                await getattr(
                    vc.channel.category,
                    f"create_{'voice' if row[0] == 'vc' else 'text'}"
                )(name=row[1].replace("!name!", member.name) \
                    .replace("!id!", str(member.id)))

    @commands.Cog.listener()
    async def on_join(self, member, _, __):
        await self.on_update("join", member)

    @commands.Cog.listener()
    async def on_leave(self, member, _, __):
        await self.on_update("leave", member)


def setup(bot):
    return
    bot.add_cog(VCChannel(bot))