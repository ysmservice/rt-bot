""""""

from discord.abc import Messageable
from discord.ext import commands
import discord

from typing import Tuple, Callable
from copy import copy


def item(name: str, callback: Callable, **kwargs) -> Tuple[Callable, Callable]:
    """アイテムのリストを簡単に作るためのもの。
    
    Parameters
    ----------
    name : str
        アイテムの種類の名前。  
        例：`discord.ui.button`の`button`
    callback : Callable
        インタラクションがきた際に呼び出されるコルーチン関数。
    **kwargs : dict
        nameで指定したdiscord.uiのアイテムに渡す引数です。"""
    return (getattr(discord.ui, name)(**kwargs), callback)


def make_view(view_name: str, items: Tuple[Tuple[Callable, Callable], ...]) -> dict:
    """RTのcomponesyに入れる辞書を簡単に作るためのもの。
    
    Parameters
    ----------
    view_name : str
        Viewの名前です。
    items : Tuple[Tuple[Callable, Callable], ...]
        `discord.ui.Button`などのアイテムとコールバックのコルーチン関数が入ったタプルのタプルです。  
        このタプルは`componesy.item`で簡単に作ることが可能です。  
        例：`(item("button", left, label="left"), item("button", right, label="right"))`

    Examples
    --------
    from rtlib import componesy

    async def on_push(view, button, interaction):
        await interaction.channel.send("Pushed!")

    @bot.command()
    async def push(ctx):
        items = (item("button", on_push, label="Push me!"),)
        view = componesy.view("PushView", items)
        await ctx.send(view=view)"""
    return {"view_name": view_name, "items": items}


class Componesy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.views = {}
        self.view = make_view
        self.bot.cogs["OnSend"].add_event(self._new_send)

    async def _new_send(self, channel, *args, **kwargs):
        # sendからコンポーネントを使えるようにする。
        items = kwargs.get("view", None)

        # rtlib.componesyによるviewならそれをdiscord.ui.Viewに交換する。
        if isinstance(items, dict):
            # viewの名前を取る。
            view_name = items["view_name"]

            # Viewがまだ作られてないなら作る。
            if view_name not in self.views:
                # discord.ui.Viewのコピーを作る。
                # このコピーからViewのクラスを作っていく。
                NewView = copy(discord.ui.View)
                # rtlib.componesyのために渡されたアイテムリストを一つづつ追加していく。
                for item, coro in items["items"]:
                    # もしメソッドなら
                    if coro.__self__ is None:
                        original_coro = coro
                    else:
                        # もしメソッドならViewに設定できないのでラップする。
                        async def original_coro(*args, **kwargs):
                            return await coro(*args, **kwargs)
                    # Viewのコピーに設定する。
                    setattr(NewView, coro.__name__, item(original_coro))
                # Viewのコピーに設定されたインタラクションの関数達をdiscord.pyは色々設定する。
                # それは__init_subclass__で行われるため、__init_subclass__を実行しておく。
                NewView.__init_subclass__()
                # キャッシュに毎回Viewを作らないようにViewクラスを保存しておく。
                self.views[view_name] = NewView
            # Viewのインスタンスを作りsendの引数viewに設定をする。
            kwargs["view"] = self.views[view_name]()

        # 引数を返す。
        return args, kwargs

    async def test_interaction(self, view, button, interaction):
        await interaction.channel.send("Pushed button.")

    @commands.command(name="_componesy_test")
    async def test(self, ctx):
        items = (item("button", self.test_interaction, label="push me"),)
        view = make_view("test", items)
        await ctx.reply("test", view=view)


def setup(bot):
    bot.add_cog(Componesy(bot))