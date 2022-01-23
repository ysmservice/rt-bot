# RT - Lib

from typing import Union, Tuple, List

from discord.ext import commands, tasks
import discord

from pymysql.err import OperationalError

from . import mysql_manager as mysql
from .data_manager import Table
from .ext import componesy
from .typed import RT


DatabaseManager = mysql.DatabaseManager


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
    wb = (wb if (wb := discord.utils.get(
            await channel.webhooks(), name=webhook_name))
          else await channel.create_webhook(name=webhook_name))
    try:
        return await wb.send(*args, **kwargs)
    except discord.InvalidArgument as e:
        if webhook_name == "RT-Tool":
            return await webhook_send(channel, *args, webhook_name="R2-Tool", **kwargs)
        else:
            raise e


# webhook_sendを新しく定義する。
discord.abc.Messageable.webhook_send = webhook_send
discord.ext.easy = componesy


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
    bot.load_extension("rtlib.rtc")
    bot.load_extension("rtlib.setting")


# discord.ext.tasksのタスクがデータベースの操作失敗によって止まることがないようにする。
default = tasks.Loop.__init__
def _init(self, *args, **kwargs):
    default(self, *args, **kwargs)
    self.add_exception_type(OperationalError)
tasks.Loop.__init__ = _init