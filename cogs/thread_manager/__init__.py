# RT - Thread Manager

from typing import TYPE_CHECKING

from discord.ext import commands
import discord

from rtlib.slash import Option
from datetime import timedelta

from .constants import MAX_CHANNELS, ERROR_RANGE
from .dataclass import DataManager

if TYPE_CHECKING:
    from aiomysql import Pool
    from rtlib import Backend


class ThreadManager(commands.Cog, DataManager):
    def __init__(self, bot: "Backend"):
        self.bot = bot
        self.pool: "Pool" = self.bot.mysql.pool
        super(commands.Cog, self).__init__(self)

    @commands.group(
        slash_command=True, description="スレッド管理用コマンドです。", extras={
            "headding": {
                "ja": "スレッドマネージャー", "en": "Thread Manager"
            }, "parent": "ServerTool"
        }
    )
    @commands.guild_only()
    @commands.has_permissions(manage_threads=True)
    async def threading(self, ctx: commands.Context):
        """!lang ja
        --------
        スレッドマネージャーです。  
        なおスラッシュコマンドに対応しています。

        !lang en
        --------
        Thread Manager"""
        if ctx.invoked_subcommand:
            if not hasattr(ctx, "interacton"):
                await ctx.trigger_typing()
        else:
            await ctx.reply(
                {"ja": "使用方法が違います。",
                 "en": "It is used in different ways."}
            )

    @threading.command(
        "list", description="設定されている監視対象チャンネルの一覧を表示します。",
        aliases=["l", "一覧"]
    )
    async def list_(self, ctx: commands.Context):
        """!lang ja
        --------
        RTに設定されているスレッドが勝手にアーカイブされないように監視しているチャンネルの一覧です。

        Aliases
        -------
        l, 一覧

        !lang en
        --------
        This is a list of channels monitored so that threads set to RT are not automatically archived.

        Aliases
        -------
        l"""
        await ctx.reply(
            embed=discord.Embed(
                title={
                    "ja": "スレッド監視対象チャンネル",
                    "en": "Inspection Target Channels"
                }, description="\n".join(
                    f"・{channel.mention}"
                    for channel in (await self.get_data(ctx.guild.id)
                        .get_channels()).values()
                ), color=self.bot.colors["normal"]
            )
        )

    NOT_CHANNEL = {
        "ja": "チャンネルを指定してください。",
        "en": "Please select channel."
    }

    @threading.command(
        description="指定したチャンネルにあるスレッドがアーカイブされないように監視します。",
        aliases=["watch", "it", "監視", "inspect"]
    )
    async def monitor(
        self, ctx, *, channel: Option(
            discord.TextChannel, "channel", "監視するスレッドのある対象のチャンネルです。"
        )
    ):
        """!lang ja
        --------
        指定されたチャンネルのスレッドが勝手に閉じられないように設定します。

        Parameters
        ----------
        channel : テキストチャンネルの名前またはメンション
            自動アーカイブを防止するために監視をする対象のチャンネルです。

        Aliases
        -------
        mon, 監視, it, inspect, watch

        !lang en
        --------
        Prevents the thread of the specified channel from being closed by itself.

        Parameters
        ----------
        channel : Name or Mention of the text channel.
            This is the channel to be monitored to prevent automatic archiving.

        Aliases
        -------
        mon, it, inspect, watch"""
        if isinstance(channel, discord.TextChannel):
            await self.get_data(ctx.guild.id).add_channel(channel.id)
            await ctx.reply("Ok")
        else:
            await ctx.reply(self.NOT_CHANNEL)

    @threading.command(
        description="スレッド監視をしているチャンネルを監視解除します。",
        aliases=["unwatch", "unit", "監視解除", "uninspect"]
    )
    async def unmonitor(
        self, ctx, *, channel: Option(
            discord.TextChannel, "channel", "監視解除する対象のチャンネルです。"
        )
    ):
        """!lang ja
        --------
        スレッドが自動アーカイブされないように監視しているチャンネルの監視を解除するコマンドです。

        Parameters
        ----------
        channel : テキストチャンネルの名前またはメンション
            監視を解除する対象のチャンネルです。

        Aliases
        -------
        unwatch, uninspect, unit, 監視解除

        !lang en
        --------
        This command is used to unmonitor a channel that is being monitored to prevent threads from being automatically archived.

        Parameters
        ----------
        channel : Name or Mention of the text channel
            The channel to be unmonitored.

        Aliases
        -------
        unwatch, uninspect, unit"""
        if isinstance(channel, discord.TextChannel):
            await self.get_data(ctx.guild.id).remove_channel(channel.id)
            await ctx.reply("Ok")
        else:
            await ctx.reply(self.NOT_CHANNEL)

    @threading.command(
        description="このコマンドを実行したスレッドに指定されたユーザーを参加させます。",
        aliases=["add", "追加", "a"]
    )
    async def join(
        self, ctx: commands.Context, *, user: Option(
            discord.Member, "user", "スレッドに参加させるユーザーです。"
        )
    ):
        """!lang ja
        --------
        このコマンドを実行したスレッドにユーザーを参加させます。

        Parameters
        ----------
        user : メンバーの名前またはメンション
            スレッドに参加させるメンバーです。

        Aliases
        -------
        add, a, 追加

        !lang en
        --------
        This command will join a user to the thread in which it is executed.  
        This will allow you to add other members to the thread without having to do any mentions.

        Parameters
        ----------
        user : Member's name or Mention
            The member to join the thread.

        Aliases
        -------
        add, a"""
        assert isinstance(ctx.channel, discord.Thread), "チャンネルでないといけません。"
        await ctx.channel.add_user(user)
        await ctx.reply("Ok")

    @threading.command(
        description="このコマンドを実行したスレッドから指定されたユーザーをキックします。",
        aliases=["k", "rm", "remove", "キック", "追放"]
    )
    async def kick(
        self, ctx: commands.Context, *, user: Option(
            discord.Member, "user", "スレッドから追い出すユーザーです。"
        )
    ):
        """!lang ja
        --------
        このコマンドを実行したスレッドから指定したメンバーを退出させます。

        Parameters
        ----------
        user : メンバーの名前またはメンション
            スレッドから退出させるメンバーです。

        Aliases
        -------
        k, rm, remove, キック, 追放

        !lang en
        --------
        Kicks the specified member from the thread where this command was executed.

        Parameters
        ----------
        user : Member's name or Mention
            The member to be kicked from the thread.

        Aliases
        -------
        k, rm, remove"""
        assert isinstance(ctx.channel, discord.Thread), "チャンネルでないといけません。"
        await ctx.channel.remove_user(user)
        await ctx.reply("Ok")

    @kick.error
    async def on_addkick_error(self, ctx, error):
        if isinstance(error, AssertionError):
            if "チャンネル" in str(error):
                await ctx.reply(
                    {"ja": "スレッドのみこのコマンドを実行できます。",
                     "en": "This command can run only thread."}
                )
            else:
                await ctx.reply(
                    {"ja": "これ以上追加できません。",
                     "en": f"I can't add the channel more than {MAX_CHANNELS}."}
                )
        elif isinstance(error, discord.HTTPException):
            if ctx.command.name == "add":
                await ctx.reply(
                    {"ja": "既にユーザーは追加されています。",
                     "en": "The user is already added."}
                )
            else:
                await ctx.reply(
                    {"ja": "そのユーザーはスレッドにいません。",
                     "en": "The user is not founc from thread."}
                )

    @commands.Cog.listener()
    async def on_thread_update(self, before: discord.Thread, after: discord.Thread):
        if (after.archived and not after.locked
            and after.parent.id in await (
                self.get_data(after.guild.id)
            ).get_channels()
        ):
                # 自動ロックされたならロックを解除する。
                await after.edit(archived=False)


def setup(bot):
    bot.add_cog(ThreadManager(bot))