# RT - Slash, Author: tasuren, Description: このコードだけはパブリックドメインとします。

from typing import TYPE_CHECKING, Optional, Union, Literal, get_origin

from discord.ext.commands.view import StringView
from discord.ext.commands.bot import BotBase
from discord.ext import commands
import discord

from datetime import datetime
from functools import wraps
from re import sub

from pytz import utc

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
            or command.description != ""
        ) or command.parent)
    ) and "jishaku" not in command.qualified_name


def camel2snake(text: str) -> str:
    "キャメルケースをスネークケースにします。"
    if text == "RT":
        return "rt"
    return sub(
        "(.[A-Z])", lambda x: f"{x.group(1)[0]}_{x.group(1)[1]}", text
    ).lower()


def make_command_instance(decorator, function: commands.Command):
    "渡されたデコレータで渡されたコマンドをスラッシュコマンドのインスタンスにします。"
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
    # `discord.SlashOption`のインスタンスを引数のデフォルトに置くことでスラッシュコマンドの引数の詳細を設定できる。
    # だが、それだとコマンドフレームワーク内で実行した際に`discord.SlashOption`に設定した`default`が渡されない。
    # それを修正するようにする。
    original_function = function.callback
    @wraps(original_function)
    async def new_function(*args, **kwargs):
        for key in list(kwargs.keys()):
            if isinstance(kwargs[key], discord.SlashOption):
                if not kwargs[key].required:
                    kwargs[key] = kwargs[key].default
        return await original_function(*args, **kwargs)
    function._callback = new_function
    return decorator(**kwargs)(
        getattr(function, "_important_callback", function.callback)
    )


def get_category_name(function: commands.Command) -> Optional[str]:
    "カテゴリーの名前取り出すだけ。"
    return function.__original_kwargs__.get("category") \
        or function.extras.get("parent")


#   ここからしばらくモンキーパッチ
# 通常のコマンドのデコレータを拡張する。
def make_command_monkey(decorator):
    @wraps(decorator)
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
                fake._category_command = True
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
def make_group_command_monkey(decorator_, group = False):
    def group_command(*args, **kwargs):
        decorator = decorator_(*args, **kwargs)
        @wraps(decorator)
        def new_decorator(function):
            function: commands.Command = decorator(function)
            if hasattr(function.parent, "slash") and check(function):
                if getattr(function.parent, "_important_callback", False):
                    # グループコマンドの真相度三つ目移行のコマンドの場合は何もしないで以下を設定しておく。
                    # 理由は下の`subcommand_dummy`にて説明されている。
                    function._important_callback = True
                else:
                    # サブコマンドを登録する。
                    if group and not getattr(
                        function.parent.slash, "_category_command", False
                    ):
                        # もし親コマンドがカテゴリーコマンドではないかつ登録したコマンドがグループコマンドの場合(深層度が3以上になるグループコマンドの集団の場合)はDiscordが対応していないので別のコマンドに交換する。
                        # その別のコマンドはグループコマンドではなく普通のコマンドで引数をひとつ取る。
                        # その引数にその先のコマンドをお手数だが書いてもらう。
                        async def subcommand_dummy(
                            self, ctx, *, command: str = discord.SlashOption(
                                "command", "この先のコマンドです。お手数ですがヘルプをご確認ください。"
                            )
                        ):
                            # ここは実行されることがない。理由は`on_interaction`を見ればわかる。
                            ...
                        function._important_callback = wraps(function.callback) \
                            (subcommand_dummy)
                    function.slash = make_command_instance(
                        function.parent.slash.subcommand, function
                    )
            return function
        return new_decorator
    return group_command
commands.GroupMixin.command = make_group_command_monkey(commands.GroupMixin.command)
commands.GroupMixin.group = make_group_command_monkey(commands.GroupMixin.group, True)


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


# 複数のコグに同じカテゴリーを親コマンドとするコマンドがあると同然かぶるのでスラッシュコマンドを登録できない。
# それを治すために`add_cog`を拡張する。
# 既に他のコグにてカテゴリーの親コマンドがあるかを調べてあるならそれを親コマンドとなるように変更を加えるように拡張する。
# また`discord.ClientCog._read_methods`を呼び出すタイミングもずらす。
original_read_methods = discord.ClientCog._read_methods
discord.Client._read_methods = lambda _: None
original_add_cog = BotBase.add_cog
def new_add_cog(self: BotBase, cog: commands.Cog, *args, **kwargs):
    # 追加されたコグの中身を取り出していく。
    for name, value in list(cog.__class__.__dict__.items()):
        # カテゴリーの親コマンドかどうかを調べる。
        if name.startswith("_slash_nc_"):
            # 全てのコグを調べて既にカテゴリーの親コマンドがあるコグがあるか調べる。
            for other in self.cogs.values():
                for oname, ovalue in list(other.__class__.__dict__.items()):
                    if oname == name:
                        # もしカテゴリーの親コマンドが既に他のコグにて尊くされているのなら親コマンドのすり替え等を行う。
                        ovalue.children.update(value.children)
                        for cname, child in list(value.children.items()):
                            ovalue.children[cname] = child
                            child.parent_command = ovalue
                        # 被った元のカテゴリーの親コマンドは子供が移行済みでもういらないので消す。
                        delattr(cog.__class__, name)
                        break
                else:
                    continue
                break
    # 色々処理をした後に本来ならコグのインスタンス化時に実行される`discord.ClientCog._read_methods`を実行する。
    original_read_methods(cog)
    return original_add_cog(self, cog, *args, **kwargs)
BotBase.add_cog = wraps(original_add_cog)(new_add_cog)


# スラッシュに対応していないがコマンドフレームワークでは対応しているようなアノテーションをスラッシュに対応させるようにする。
original_get_type = discord.CommandOption.get_type
def new_get_type(self, typing: type):
    if typing in (
        discord.TextChannel, discord.VoiceChannel,
        discord.Thread, discord.StageChannel
    ):
        # `discord.TextChannel`等にしている場合は`discord.abc.GuildChannel`とする。
        return discord.CommandOption.option_types[discord.abc.GuildChannel]
    elif any(get_origin(typing) is type_ for type_ in (Union, Literal)) or hasattr(typing, "converter"):
        # `typing.Union`や`typing.Literal`をアノテーションに使うことはできないので、これらのオプションを見つけたら文字列の型として返すように設定する。
        # また、`commands.Converter`か`commands.Converter`を継承したクラスの場合は文字列とする。
        return discord.CommandOption.option_types[str]
    else:
        # 上記以外なら元々の関数を実行する。
        return original_get_type(self, typing)
discord.CommandOption.get_type = new_get_type


# スラッシュコマンド等を登録するのがイベント`on_connect`が呼ばれた時に設定されている。
# RTではコグを`on_ready`が呼び出された後に読み込むためスラッシュコマンドがこれだと登録されない。
# そのため登録されるようにする。
del discord.Client.on_connect
discord.Client.on_full_ready = discord.Client.rollout_global_application_commands


#   ここからモンキーパッチではない。
class Context:
    "`discord.Interaction`を使った`commands.Context`少互換のContextクラスです。"

    def __init__(
        self, bot: commands.Bot, interaction: discord.Interaction,
        command: commands.Command, content: str
    ):
        self.interaction = interaction
        self.author, self.channel = interaction.user, interaction.channel
        self.guild, self.send = interaction.guild, self.channel.send
        self.voice_client = getattr(self.guild, "voice_cilent", None)
        self.fetch_message, self.message = self.channel.fetch_message, self
        self.typing, self.trigger_typing = self.channel.typing, self.channel.trigger_typing

        self.invoked_subcommand, self._state = False, bot._connection
        self.bot, self.prefix = bot, "/"
        self.cog, self.command = command.cog, command
        self.content, self.ctx = content, self
        self.edited_at, self.created_at = None, datetime.now(utc)

    async def reply(self, *args, **kwargs):
        for key in list(kwargs.keys()):
            if key not in self.interaction.response.send_message.__annotations__:
                # `discord.InteractionResponse.send_message`にない引数の値は消しておく。
                del kwargs[key]
        await self.interaction.response.send_message(*args, **kwargs)

# スラッシュコマンドのテストと登録とその他を入れるコグ
class SlashManager(commands.Cog):
    def __init__(self, bot: "RT"):
        self.bot = bot
        # `process_application_commands`を実行するon_interactionが内部で設定されている。
        # それを上書きする。
        bot.event(self.on_interaction)

    async def on_interaction(self, interaction: discord.Interaction):
        # ここで親コマンドがカテゴリーのコマンドが実行された際にコマンドフレームワークを介してそのコマンドを実行する。
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
                    # Contextを準備してコマンドフレームワークのコマンドを実行する。
                    ctx = Context(self.bot, interaction, command, content)
                    processed_ctx = await self.bot.get_context(ctx)
                    ctx.view = processed_ctx.view
                    ctx.args, ctx.kwargs = processed_ctx.args, processed_ctx.kwargs
                    for name, value in processed_ctx.__dict__.items():
                        if not name.startswith(
                            (
                                "__", "send", "reply", "trigger", "typing",
                                "created", "channel", "message", "guild"
                            )
                        ):
                            setattr(ctx, name, value)
                    return await self.bot.invoke(ctx.message)
        # コマンドフレームワークのコマンド実行以外のInteractionなら元々のやつに渡す。
        await self.bot.process_application_commands(interaction)

    @commands.command(description="コマンドを実行します。 | Run command", category="RT")
    async def run(self, ctx: Context, *, content):
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

    @commands.Cog.listener()
    async def on_full_ready(self):
        ...

    # ここから完全なテスト用コマンド
    @discord.slash_command()
    @commands.cooldown(1, 30)
    async def normal_test(self, interaction):
        await interaction.response.send_message("test")

    @commands.command(
        headding={"ja": "テスト見出し", "en": "..."}, category="SlashTest"
    )
    async def test(self, ctx, test: Union[str, int]):
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