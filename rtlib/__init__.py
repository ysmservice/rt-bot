# RTLib - (C) 2021 RT-Team
# Author : tasuren

from discord.ext import commands
import discord

from typing import Union, Tuple, List
from copy import copy

from .web_manager import WebManager
from .backend import *
from . import mysql_manager as mysql
from .oauth import OAuth



async def webhook_send(
        channel, *args, webhook_name: str = "RT-Tool", **kwargs):
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
    await wb.send(*args, **kwargs)


discord.abc.Messageable.webhook_send = webhook_send


def setup(bot, only: Union[Tuple[str, ...], List[str]] = []):
    """rtlibにあるエクステンションを全てまたは指定されたものだけ読み込みます。

    Notes
    -----
    これを使えば正しい順番で読み込まれるため、通常はこれを使い一括でRTのエクステンションを読み込むべきです。

    Parameters
    ----------
    bot
        DiscordのBotです。
    only : Union[Tuple[str, ...], List[str]], optional
        読み込むエクステンションを限定します。  
        例：`("componesy", "embeds")`とすれば`componesy`と`embeds`のみを正しい順番で読み込みます。"""
    for name in ("embeds", "on_full_reaction", "dochelp"):
        if name in only or only == []:
            try:
                bot.load_extension("rtlib.ext." + name)
            except commands.errors.ExtensionAlreadyLoaded:
                pass
