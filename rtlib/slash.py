# RT - Slash

from typing import TYPE_CHECKING, Optional

from discord.ext import commands
import discord

from inspect import signature
from functools import wraps
from re import sub

if TYPE_CHECKING:
    from . import RT


def check(command: commands.Command):
    "スラッシュにふさわしいかチェックする関数です。"
    return (
        ((
            "category" in command.__original_kwargs__ 
            or "parent" in command.extras
        ) and (
            "headding" in command.__original_kwargs__
            or "headding" in command.extras
        ) or command.parent)
    ) and "jishaku" not in command.qualified_name


def camel2snake(text: str) -> str:
    "キャメルケースをスネークケースにします。"
    return sub(
        "(.[A-Z])", lambda x: f"{x.group(1)[0]}_{x.group(1)[1]}", text
    ).lower()


def make_command_instance(decorator, function):
    "渡されたデコレータで渡された関数をスラッシュコマンドのインスタンスにします。"
    kwargs = {
        name: function.__original_kwargs__[name]
        for name in decorator.__annotations__
        if name in function.__original_kwargs__
    }
    kwargs["name"] = camel2snake(function.name)
    kwargs["description"] = function.description or function.__original_kwargs__.pop(
        "headding", function.extras.get("headding", {})
    ).get("ja", None)
    if kwargs["description"] is None:
        del kwargs["description"]
    return decorator(**kwargs)(function.callback)


def get_category_name(function: commands.Command) -> Optional[str]:
    "カテゴリーの名前取り出すだけ。"
    return function.__original_kwargs__.get("category") \
        or function.extras.get("parent")


#   ここからしばらくモンキーパッチ
# 通常のコマンドのデコレータを拡張する。
def make_command_monkey(decorator):
    def normal_command(*args, _deco_rator_=decorator, **kwargs):
        decorator = _deco_rator_(*args, **kwargs)
        @wraps(decorator)
        def new_decorator(function):
            function = decorator(function)
            if check(function):
                # カテゴリーを親コマンドとして設定したいので、ここでそのカテゴリーの親コマンドとする偽の関数を用意する。
                category_name = get_category_name(function)
                @discord.slash_command(category_name := camel2snake(category_name))
                async def fake(self, _):
                    ...
                # おかしいことなるので関数の名前をしっかりと設定しておく。
                fake._callback.__name__ = category_name
                # オリジナルのカテゴリー分けされているコマンドフレームワークのコマンドに新しい属性`slash`を生やす。
                # カテゴリーの親コマンドの偽関数は`ApplicationCommand`にラップされているはずで、それのサブコマンドデコレータを使いオリジナルの関数を`ApplicationSubcommand`でラップして、それをその`slash`に入れておく。
                # また、のちのち他の同じカテゴリーに属するコマンドを同じカテゴリーの親コマンドと統合するので、生き残れるカテゴリーの親コマンドは一体のみになる。
                function.slash = make_command_instance(fake.subcommand, function)
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
            if hasattr(function.parent, "slash") and check(function):
                # サブコマンドを登録する。
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
    for name, function in list(cls.__dict__.items()):
        if not (
            isinstance(function, commands.Command) and hasattr(function, "slash")
        ) or not (category := get_category_name(function)):
            continue
        # 大文字だとコマンド名に使えない。
        # なのにカテゴリーの名前がキャメルケースになっているのでスネークケースに修正する。
        category = camel2snake(category)

        # 一番上のカテゴリーの親コマンドの関数をクラスに設定しておく。
        if not hasattr(cls, name := f"_slash_nc_{category}"):
            # 一番上でモンキーパッチ
            fake = function.slash.parent_command
            fake._callback.__name__ = name
            setattr(cls, name, fake)
            # 設定したカテゴリーの親コマンドに設定されている他のコマンドも設定する。
            for other_name, other in list(cls.__dict__.items()):
                if (name != other_name and hasattr(other, "slash")
                        and category == other.slash.parent_command
                            .callback.__name__):
                    other.slash.parent_command = function.slash.parent_command
                    function.slash.parent_command.children[other.slash.name] = \
                        other.slash
    self = original(cls, *args, **kwargs)
    # カテゴリーの親コマンドのサブコマンドの`ApplicationSubcommand`/`ApplicationCommand`のインスタンスにコグのクラスのself引数を設定する。
    # これを設定する理由は本来であれば自動で`ApplicationSubcommand`/`ApplicationCommand`のインスタンスに内部で`self`を設定してくれる。
    # だが、この場合はコマンドフレームワークのコマンドのクラスのインスタンスであるため自動で設定されないのでここで設定する。
    for name, function in list(cls.__dict__.items()):
        if hasattr(function, "slash"):
            if not function.slash._self_argument:
                function.slash.set_self_argument(self)
    return self
commands.Cog.__new__ = new_new


#   ここからモンキーパッチではない。
class Context:
    "`discord.Interaction`を使った`commands.Context`少互換のContextクラスです。"

    def __init__(
        self, bot: commands.Bot, interaction: discord.Interaction,
        command: commands.Command, content: str
    ):
        self.interaction = interaction
        self.author, self.channel = interaction.user, interaction.channel
        self.guild, self.message = interaction.guild, interaction.message
        self.voice_client = getattr(self.guild, "voice_cilent", None)
        self.fetch_message = self.channel.fetch_message
        self.send, self.reply = self.channel.send, self.interaction.response.send_message
        self.typing, self.trigger_typing = self.channel.typing, self.channel.trigger_typing

        self.invoked_subcommand, self._state = False, bot._connection
        self.bot, self.prefix = bot, "/"
        self.cog, self.command = command.cog, command
        self.content, self.ctx = content, self


# スラッシュコマンドのテストと登録とその他を入れるコグ
class SlashManager(commands.Cog):
    def __init__(self, bot: "RT"):
        self.bot = bot
        # `process_application_commands`を実行するon_interactionが内部で設定されている。
        # それを上書きする。
        bot.event(self.on_interaction)

    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.application_command:
            for command in self.bot.commands:
                if (interaction.data.get("options", ())
                        and command.name == interaction.data["options"][0]["name"]):
                    # コマンドのメッセージの内容を作る。
                    data = interaction.data["options"][0]
                    content = f"{self.bot.command_prefix[0]}{data['name']}"
                    while "options" in data:
                        if not data["options"]:
                            break
                        if "value" in data["options"][0]:
                            # 引数
                            length = len(data)
                            for count, option in enumerate(data["options"], 1):
                                if isinstance(option["value"], dict):
                                    # もしユーザーが入れた引数の値が辞書の場合はIDを取る。
                                    # これはこの場合は`discord.Member`等のDiscordオブジェクトのデータのためです。
                                    option["value"] = str(option["value"]["id"])
                                if count != length and (
                                    " " in option["value"] or "\n" in option["value"]
                                ):
                                    # 最後の引数ではないかつ空白または改行が含まれている場合は`"`で囲む。
                                    option["value"] = f'"{option["value"]}"'

                                content += f" {option['value']}"
                            break
                        else:
                            # サブコマンド
                            data = data["options"][0]
                            content += f" {data['name']}"
                    return await self.bot.process_commands(
                        Context(self.bot, interaction, command, content)
                    )
        # コマンドフレームワークのコマンド実行以外のInteractionなら元々のやつに渡す。
        await self.bot.process_application_commands(interaction)

    @commands.command(description="コマンドを実行します。 | Run command", category="BotGeneral")
    async def command(self, ctx: Context, *, content):
        """!lang ja
        --------
        RTコマンドを実行します。  
        これはスラッシュコマンドから`rt!...`のようなコマンドを実行するためのものです。  
        本当は全てのコマンドがスラッシュにないといけないのですが一応用意したものです。  
        もしヘルプにないコマンドを見つけたけどスラッシュから実行したいとか思ったらこれ使いましょう。

        Parameters
        ----------
        content : str
            コマンド本文です。

        Examples
        --------
        `/command ping`

        !lang en
        --------
        Execute the RT command.  
        This is a slash command to `rt! This is for executing commands like `rt!  
        In fact, all commands should be in the slash, but I prepared it just in case.  
        If you find a command that is not in the help but you want to execute it from a slash, use this.

        Parameters
        ----------
        content : str
            The body of the command.

        Examples
        --------
        `/command ping`"""
        if "command " in content:
            await ctx.reply("使えないワードがあります。")
        else:
            if not content.startswith(tuple(self.bot.command_prefix)):
                content = f"{self.bot.command_prefix[0]}{content}"
            ctx.content = content
            await self.bot.process_commands(ctx)

    # ここから完全なテスト用コマンド
    @discord.slash_command()
    @commands.cooldown(1, 30)
    async def normal_test(self, interaction):
        await interaction.response.send_message("test")

    @commands.command(
        headding={"ja": "テスト見出し", "en": "..."}, category="SlashTest"
    )
    async def test(self, ctx):
        await ctx.reply("This is the test")

    @commands.group(
        headding={"ja": "テストグループ", "en": "..."}, category="SlashTest"
    )
    async def test_group(self, ctx):
        ...

    @test_group.command()
    async def wow(self, ctx, member: discord.Member = discord.SlashOption("member", "This is the test")):
        await ctx.reply(f"This is the test. {member.name}")

    @test_group.command()
    async def ping(self, ctx):
        await ctx.reply("pong")


def setup(bot):
    bot.add_cog(SlashManager(bot))