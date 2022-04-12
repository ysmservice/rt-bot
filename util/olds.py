# RT utils - Old features

from typing import Optional, Union, Tuple, List

from discord.ext import commands, tasks # type: ignore
import discord

from pymysql.err import OperationalError

# from .slash import Context as SlashContext
# from .ext import componesy
from .cacher import CacherPool


def similer(before: str, after: str, check_length: int) -> bool:
    "beforeがafterとcheck_lengthの文字数分似ているかどうかをチェックします。"
    return any(after[i:i + check_length] in before
               for i in range(len(after) - check_length))


def role2obj(guild: discord.Guild, arg: str) -> list[Optional[discord.Role]]:
    "`役職1, 役職2, ...`のようになってるものをロールオブジェクトに変換します。"
    roles_raw, roles = arg.split(','), []
    for role in roles_raw:
        if '@' in role:
            roles.append(guild.get_role(int(role[3:-1])))
        elif check_int(role):
            roles.append(guild.get_role(int(role)))
        else:
            roles.append(discord.utils.get(guild.roles, name=role))
    return roles


class Roler(commands.Converter):
    "`role2obj`のコンバーターです。現在は非推奨です。rtutil.RolesConverterを使ってください。"
    async def convert(self, ctx, arg):
        return role2obj(ctx.guild, arg)


async def get_webhook(
    channel: discord.TextChannel, name: str = "RT-Tool"
) -> Optional[discord.Webhook]:
    "ウェブフックを取得します。"
    return discord.utils.get(await channel.webhooks(), name=name)


class FakeMessageForCleanContent:
    def __init__(
        self, guild: Optional[discord.Guild], content: str
    ):
        self.guild, self.content = guild, content
        self.mentions = self._get("member", "")
        self.role_mentions, self.channel_mentions = \
            self._get("role"), self._get("channel")

    def _get(self, get_mode, mentions_mode=None):
        return [
            getattr(self.guild, f"get_{get_mode}")(mention)
            for mention in getattr(
                self, f"raw_{f'{get_mode}_' if mentions_mode is None else mentions_mode}mentions"
            )
        ]
for name in ("clean_content", "raw_mentions", "raw_role_mentions", "raw_channel_mentions"):
    setattr(FakeMessageForCleanContent, name, getattr(discord.Message, name))
def clean_content(content: str, guild: discord.Guild) -> str:
    "渡された文字列を綺麗にします。"
    return FakeMessageForCleanContent(guild, content).clean_content


# Context = Union[SlashContext, commands.Context]


async def webhook_send(
    channel, *args, webhook_name: str = "RT-Tool", **kwargs
):
    """`channel.send`感覚でウェブフック送信をするための関数です。  
    `channel.webhook_send`のように使えます。  
    
    Parameters
    ----------
    *args : tuple
        discord.pyのWebhook.sendに入れる引数です。
    webhook_name : str, defualt "RT-Tool"
        使用するウェブフックの名前です。  
        存在しない場合は作成されます。
    **kwargs : dict
        discord.pyのWebhook.sendに入れるキーワード引数です。"""
    if isinstance(channel, commands.Context):
        channel = channel.channel
    wb = (wb if (wb := await get_webhook(channel, webhook_name))
          else await channel.create_webhook(name=webhook_name))
    try:
        return await wb.send(*args, **kwargs)
    except discord.InvalidArgument as e:
        if webhook_name == "RT-Tool":
            return await webhook_send(channel, *args, webhook_name="R2-Tool", **kwargs)
        else:
            raise e


# webhook_sendを新しく定義する。
# discord.abc.Messageable.webhook_send = webhook_send # type: ignore
# discord.ext.easy = componesy # type: ignore


def setup(bot, only: Union[Tuple[str, ...], List[str]] = []):
    "rtlibにあるエクステンションを全てまたは指定されたものだけ読み込みます。"
    bot.load_extension("rtlib.data_manager")
    for name in ("on_send", "on_full_reaction", "dochelp", "debug", "on_cog_add"):
        if name in only or only == []:
            try:
                bot.load_extension("rtlib.ext." + name)
            except commands.ExtensionAlreadyLoaded:
                pass
    bot.load_extension("rtlib.websocket")
    bot.load_extension("rtlib.rtws")
    bot.load_extension("rtlib.setting")
    bot.cachers = CacherPool()


# discord.ext.tasksのタスクがデータベースの操作失敗によって止まることがないようにする。
if not getattr(tasks.Loop, "_rtutil_extended", False):
    default = tasks.Loop.__init__
    def _init(self, *args, **kwargs):
        default(self, *args, **kwargs)
        self.add_exception_type(OperationalError)
        self.add_exception_type(discord.DiscordServerError)
    tasks.Loop.__init__ = _init
    tasks.Loop._rtutil_extended = True


def sendKwargs(ctx, **kwargs):
    if isinstance(ctx, commands.Context):
        for key in list(kwargs.keys()):
            if (key not in discord.abc.Messageable.send.__annotations__
                    and key in discord.InteractionResponse
                        .send_message.__annotations__):
                del kwargs[key]
    return kwargs
