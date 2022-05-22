# Free RT - Logger

from discord.ext import commands, tasks
import discord

from traceback import TracebackException

import collections

from util import RT


ERROR_CHANNEL = 962977145716625439


class SystemLog(commands.Cog):
    def __init__(self, bot: RT):
        self.bot = bot
        self.names = []
        self.zero_parents = []
        self.authors = []
        self.guilds = []
        self.errors = set()
        self.logging_loop.start()

    def cog_unload(self):
        self.logging_loop.cancel()

    def _make_embed(self):
        name = collections.Counter(self.names).most_common()[0]
        zero_parent = collections.Counter(self.zero_parents).most_common()[0]
        author = collections.Counter(self.authors).most_common()[0]
        guild = collections.Counter(self.guilds).most_common()[0]
        e = discord.Embed(
            title="Free RT command log",
            description=f"1分間で{len(self.names)}回のコマンド実行(以下、実行最多記録)",
            color=self.bot.Colors.unknown
        )
        e.add_field(name="コマンド", value=f"{name[0]}：{name[1]}回")
        e.add_field(name="コマンド(Group)", value=f"{zero_parent[0]}：{zero_parent[1]}回")
        e.add_field(
            name="ユーザー",
            value=f"{self.bot.get_user(author[0])}({author[0]})：{author[1]}回"
        )
        e.add_field(
            name="サーバー",
            value=f"{self.bot.get_guild(guild[0])}({guild[0]})：{guild[1]}回"
        )
        return e

    @tasks.loop(seconds=60)
    async def logging_loop(self):
        if len(self.names) != 0:
            await self.bot.get_channel(961870556548984862) \
                .send(embed=self._make_embed())
            self.names = []
            self.zero_parents = []
            self.authors = []
            self.guilds = []

    @commands.Cog.listener()
    async def on_command(self, ctx):
        self.names.append(ctx.command.name)
        self.zero_parents.append(
            ctx.command.name if len(ctx.command.parents) == 0 
            else ctx.command.parents[-1].name
        )
        self.authors.append(ctx.author.id)
        self.guilds.append(getattr(ctx.guild, "id", 0))

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        # エラー時のログ処理。大量のisinstance->returnがあるのはcogs/RT/__init__.pyで処理するから。
        if isinstance(
            error,
            (commands.CommandNotFound, discord.Forbidden, commands.CommandOnCooldown,
             commands.MemberNotFound, commands.UserNotFound, commands.ChannelNotFound,
             commands.RoleNotFound, commands.MissingRequiredArgument, commands.BadArgument,
             commands.ArgumentParsingError, commands.TooManyArguments, commands.MissingPermissions,
                commands.MissingRole, commands.CheckFailure, AssertionError)):
            return
        elif isinstance(error, commands.CommandInvokeError):
            return await self.on_command_error(ctx, error.original)
        elif isinstance(error, AttributeError) and "VoiceChannel" in str(error):
            return
        else:
            error_message = "".join(TracebackException.from_exception(error).format())
            print("\033[31m" + error_message + "\033[0m")
            ch = self.bot.get_channel(ERROR_CHANNEL)
            embed = discord.Embed(
                title="Free RT Error log",
                description=f"```{error_message}```",
                color=self.bot.Colors.unknown
            )
            embed.add_field(name="コマンド", value=f"{ctx.command.name} (実行メッセージ: {ctx.message.content})")
            embed.add_field(name="ユーザー", value=f"{ctx.author.mention} ({ctx.author.id})")
            embed.add_field(name="サーバー", value=f"{ctx.guild.name} ({ctx.guild.id})")
            await ch.send(embed=embed)


async def setup(bot):
    await bot.add_cog(SystemLog(bot))
