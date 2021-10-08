# RT.cogs.music - Util

from typing import TYPE_CHECKING

from discord.ext import commands
import discord

if TYPE_CHECKING:
    from normal import MusicNormal


async def check_dj(cog: "MusicNormal", ctx: commands.Context) -> bool:
    # 渡されたメンバーがDJ役職を持っているか確認します。
    try:
        role_id = await cog.read_dj(ctx.guild.id)
    except AssertionError:
        role_id = 0
    return (
        len([m for m in ctx.author.voice.channel.members if not m.bot]) == 1
        or (
            (not role_id and discord.utils.get(ctx.author.roles, name="DJ"))
            or discord.utils.get(ctx.author.roles, id=role_id)
        ) or ctx.author.guild_permissions.mute_members
    )
