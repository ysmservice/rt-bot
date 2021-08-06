# RTLib - (C) 2021 RT-Team
# Author : tasuren

from discord.ext import commands
from typing import Union, Tuple, List

from .web_manager import WebManager
from .backend import *
from . import mysql_manager as mysql
from .oauth import OAuth


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
