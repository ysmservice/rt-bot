# RT - Slash

from typing import TYPE_CHECKING, TypeVar

from discord.ext import commands
import discord

from functools import wraps

if TYPE_CHECKING:
    from . import RT


class Context:
    def __init__(
        self, bot: commands.Bot, interaction: discord.Interaction,
        command: commands.Command
    ):
        self.interaction = interaction
        self.author, self.channel = interaction.user, interaction.channel
        self.guild, self.message = interaction.guild, interaction.message
        self.voice_client = getattr(self.guild, "voice_cilent", None)
        self.fetch_message = self.channel.fetch_message
        self.send, self.reply = self.channel.send, self.interaction.response.send_message
        self.typing, self.trigger_typing = self.channel.typing, self.channel.trigger_typing

        self.invoked_subcommand = False
        self.bot, self.prefix = bot, "/"
        self.cog, self.command = command.cog, command


FT = TypeVar("FT", bound=commands.Command)
def interaction2context(func: FT) -> FT:
    "インタラクションをContext(擬似)に変換するようにするデコレータです。"
    @wraps(func)
    async def new(self, interaction: discord.Interaction, *args, **kwargs):
        return await func.callback(
            self, Context(self.bot, interaction, getattr(self, func.__name__)),
            *args, **kwargs
        )
    return new


def make_command_instance(decorator, function):
    "渡されたデコレータで渡された関数をスラッシュコマンドのインスタンスにします。"
    kwargs = {
        name: function.__original_kwargs__[name]
        for name in decorator.__annotations__
        if name in function.__original_kwargs__
    }
    kwargs["name"] = function.name
    kwargs["description"] = function.description or function.__original_kwargs__.pop(
        "headding", function.extras.get("headding", {})
    ).get("ja", None)
    return decorator(**kwargs)(interaction2context(function.callback))


# 通常のコマンドのデコレータを拡張する。
def make_command_monkey(decorator):
    def normal_command(*args, _deco_rator_=decorator, **kwargs):
        decorator = _deco_rator_(*args, **kwargs)
        @wraps(decorator)
        def new_decorator(function):
            function = decorator(function)
            function.slash = make_command_instance(discord.slash_command, function)
            return function
        return new_decorator
    return normal_command
commands.command = make_command_monkey(commands.command)
commands.group = make_command_monkey(commands.group)


# 通常のグループコマンドのサブコマンドのデコレータを拡張する
def make_group_command_monkey(decorator):
    def group_command(*args, _deco_rator_=decorator, **kwargs):
        decorator = _deco_rator_(*args, **kwargs)
        @wraps(decorator)
        def new_decorator(function):
            function = decorator(function)
            if hasattr(function.parent, "slash"):
                function.slash = make_command_instance(
                    function.parent.slash.subcommand, function
                )
            return function
        return new_decorator
    return group_command
commands.GroupMixin.command = make_group_command_monkey(commands.GroupMixin.command)
commands.GroupMixin.group = make_group_command_monkey(commands.GroupMixin.group)


# 上で行ったモンキーパッチを適用させるためにCogを拡張する。
original = commands.Cog.__new__
def new_new(cls, *args, **kwargs):
    print(cls.__dict__)
    for name, function in list(cls.__dict__.items()):
        if isinstance(function, commands.Command):
            setattr(cls, f"_slash_nc_{name}", function.slash)
    return original(cls, *args, **kwargs)
commands.Cog.__new__ = new_new


# テスト用コグ
class Slash(commands.Cog):
    def __init__(self, bot: "RT"):
        self.bot = bot

    @commands.command()
    async def test(self, ctx):
        await ctx.reply("This is the test")

    @commands.group()
    async def test_group(self, ctx):
        ...

    @test_group.command()
    async def wow(self, ctx, member: discord.Member = discord.SlashOption("member", "This is the test")):
        await ctx.reply(f"This is the test. {member.name}")

    @test_group.command()
    async def ping(self, ctx):
        await ctx.reply("pong")


def setup(bot):
    bot.add_cog(Slash(bot))