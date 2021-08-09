"""# Componesy - ボタンなどを簡単に作るためのエクステンション。
これを使えば以下のようにボタン付きのメッセージを作成できます。
```python
from rtlib.ext import componesy
from rtlib import setup

# ...

setup(bot)

# ...

async def test_interaction(view, button, interaction):
    await interaction.channel.send("Pushed button!")

@bot.command()
async def test(ctx):
    view = componesy.View("TestView")
    view.add_item("button", test_interaction, label="Push me!")
    await ctx.reply("test", view=view)
```
## 使用方法
このエクステンションの名前は`componesy`です。  
有効化方法は`bot.load_extension("rtlib.ext.componesy")`です。  
`rtlib.setup`でもいけます。  
使用方法は`coponesy.View("Viewの名前")`, `componesy.View.add_item(アイテム名, コールバック, **kwargs)`です。  
詳細は`componesy.View`のドキュメンテーションを参照してください。"""

from discord.abc import Messageable
from discord.ext import commands
import discord

from typing import Tuple, Callable
from copy import deepcopy


def add_late():
    def _componesy_add_late_decorator(coro):
        return coro
    return _componesy_add_late_decorator
discord.ui.add_late = add_late


def item(name: str, callback: Callable = None, **kwargs) -> Tuple[Callable, Callable]:
    """アイテムのリストを簡単に作るためのもの。
    
    Parameters
    ----------
    name : str
        アイテムの種類の名前。  
        例：`discord.ui.button`の`button`
    callback : Callable, default None
        インタラクションがきた際に呼び出されるコルーチン関数。  
        普通はこの引数がなければなりませんが、リンク付きボタンの場合はなくていいです。
    **kwargs : dict
        nameで指定したdiscord.uiのアイテムに渡す引数です。"""
    if name == "link_button":
        name = "add_late"
        async def new_callback(view, b_kwargs=kwargs):
            view.add_item(discord.ui.Button(**b_kwargs))
            return view
        callback, kwargs = new_callback, {}
    elif name[0] in ("B", "S"):
        name = "add_late"
        async def new_callback(view, b_kwargs=kwargs):
            view.add_item(getattr(discord.ui, name)(**b_kwargs))
            return view
        callback, kwargs = new_callback, {}
    return (getattr(discord.ui, name)(**kwargs), callback)


def make_view(view_name: str, items: Tuple[Tuple[Callable, Callable], ...]) -> dict:
    """RTのcomponesyに入れる辞書を簡単に作るためのもの。

    Notes
    -----
    discord.Embedのように作りたいなら`componesy.View`を使いましょう。  
    というかそっちのほうがきれいになる。

    Parameters
    ----------
    view_name : str
        Viewの名前です。
    items : Tuple[Tuple[Callable, Callable], ...]
        `discord.ui.Button`などのアイテムとコールバックのコルーチン関数が入ったタプルのタプルです。  
        このタプルは`componesy.item`で簡単に作ることが可能です。  
        例：`(item("button", left, label="left"), item("button", right, label="right"))`"""
    return {"view_name": view_name, "items": items}


class View:
    """Viewを簡単に作るためクラスです。

    Notes
    -----
    このComponesyを使うには`bot.load_extension("rtlib.componesy")`をしないといけません。  
    または`componesy.setup(bot)`でもいけます。  
    それと`bot.load_extension("rtlib.libs.on_send")`は読み込まれていない場合自動で読み込まれます。  
    エクステンションを読み込む必要があるということなので注意してね。

    Parameters
    ----------
    view_name : str
        Viewの名前です。  
        作ったViewを次使うときに使えるようにキャッシュする際に一緒に保存する名前です。  
        なので実行の度に変わる名前にはしないでください！

    Attributes
    ----------
    items : List[Tuple[Callable, Callable]]
        追加されてるアイテムです。
    view_name : str
        Viewの名前です。

    Examples
    --------
    from rtlib.ext import componesy

    # ...

    componesy.setup(bot)

    async def test_interaction(view, button, interaction):
        await interaction.channel.send("Pushed button!")

    @bot.command()
    async def test(ctx):
        view = componesy.View("TestView")
        view.add_item("button", test_interaction, label="Push me!")
        await ctx.reply("test", view=view)"""
    def __init__(self, view_name: str, *args, **kwargs):
        self.items: list = []
        self.view_name: str = view_name
        self._args, self._kwargs = args, kwargs
        # rtlibのViewかどうかの判別用の変数。
        self._rtlib_view = 0

    def add_item(self, item_name: str, callback: Callable = None, **kwargs) -> None:
        """Viewにアイテムを追加します。

        Parameters
        ----------
        item_name : str
            アイテム名です。  
            `discord.ui.Item`を作成するためのdiscord.pyのデコレータである`discord.ui.button`のbuttonなどを使うことができます。  
            もしリンクボタンを作りたい場合はここを`link_button`にしてcallbackを指定しないでください。  
            もしカスタムしたい場合は`add_late`にすることで、Viewのインスタンス化にcallbackが呼ばれるようにすることができます。
        callback : Callable, default None
            インタラクションがあった時呼ばれるコルーチン関数です。  
            普通これは必要な引数ですが、アイテム名が`link_button`の際は必要がないです。
        **kwargs
            `discord.ui.<item_name>`に渡すキーワード引数です。
            例：`label="ボタンテキスト"`"""
        self.items.append(item(item_name, callback, **kwargs))

    def remove_item(self, callback_name: str) -> None:
        """Viewからアイテムを削除します。

        Parameters
        ----------
        callback_name : str
            削除するアイテムのコールバックの名前です。

        Raises
        ------
        KeyError : アイテムが見つからない場合発生します。"""
        i = -1
        for item, callback in self.items:
            i += 1
            if callback.__name__ == callback_name:
                break
        if i != -1:
            self.items.pop(i)
        else:
            raise KeyError("削除するアイテムが見つかりませんでした。")

    def _make_items(self) -> dict:
        # 辞書型のアイテムに変換をする。
        return {
            "view_name": self.view_name,
            "items": self.items,
            "args": self._args,
            "kwargs": self._kwargs
        }


class Componesy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.views = {}
        self.view = make_view
        if "OnSend" not in self.bot.cogs:
            self.bot.load_extension("rtlib.ext.on_send")
        self.bot.cogs["OnSend"].add_event(self._new_send, "on_send")
        self.bot.cogs["OnSend"].add_event(self._new_send, "on_edit")

    async def _new_send(self, channel, *args, **kwargs):
        # sendからコンポーネントを使えるようにする。
        items = kwargs.get("view", None)

        # rtlib.componesyによるviewならそれをdiscord.ui.Viewに交換する。
        is_view = hasattr(items, "_rtlib_view")
        if isinstance(items, dict) or is_view:
            if is_view:
                items = items._make_items()
            # viewの名前を取る。
            view_name = items["view_name"]
            class_args, class_kwargs = items["args"], items["kwargs"]

            # Viewがまだ作られてないなら作る。
            if view_name not in self.views:
                # componesyによるアイテムを新しく作るViewに追加する関数リストに追加していく。
                functions, add_late = {}, None

                for uiitem, coro in items["items"]:
                    if uiitem.__name__.startswith("_componesy_add_late"):
                        add_late = coro
                    else:
                        if coro.__self__ is None:
                            new_coro = coro
                        else:
                            # もしメソッドならViewに設定できないのでラップする。
                            # 二重ラップしないとcoroが2個目以降のcoroと同じになる。
                            async def new_coro(*args, _coro_original=coro, **kwargs):
                                async def new_coro():
                                    return await _coro_original(*args, **kwargs)
                                return await new_coro()

                        functions[coro.__name__] = uiitem(new_coro)
                        del new_coro, coro

                # typeを使用して動的にdiscord.ui.Viewを継承した上で追加した関数をつけたクラスを作成する。
                # キャッシュに毎回Viewを作らないようにViewクラスを保存しておく。
                self.views[view_name] = type(view_name, (discord.ui.View,), functions)

            # Viewのインスタンスを作りsendの引数viewに設定をする。
            kwargs["view"] = self.views[view_name](*class_args, **class_kwargs)
            if add_late is not None:
                kwargs["view"] = await add_late(kwargs["view"])

        # 引数を返す。
        return args, kwargs

    async def test_interaction(self, view, button, interaction):
        await interaction.channel.send("Pushed button.")

    async def test_count(self, view, button, interaction):
        button.label = str(int(button.label) + 1)
        await interaction.message.edit(view=view)

    @commands.command(name="_componesy_test")
    async def test(self, ctx):
        view = View("TestView")
        view.add_item("button", self.test_interaction, label="Push me!")
        view.add_item("button", self.test_count, label="0")
        await ctx.reply("test", view=view)


def setup(bot):
    bot.add_cog(Componesy(bot))
