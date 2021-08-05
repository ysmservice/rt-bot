# rtlib - Componesy

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
    from rtlib import componesy

    # ...

    componesy.setup(bot)

    async def test_interaction(view, button, interaction):
        await interaction.channel.send("Pushed button!")

    @bot.command()
    async def test(ctx):
        view = componesy.View("TestView")
        view.add_item("button", test_interaction, label="Push me!")
        await ctx.reply("test", view=view)"""
    def __init__(self, view_name: str):
        self.items = []
        self.view_name = view_name
        # rtlibのViewかどうかの判別用の変数。
        self._rtlib_view = 0

    def add_item(self, item_name: str, callback: Callable, **kwargs) -> None:
        """Viewにアイテムを追加します。

        Parameters
        ----------
        item_name : str
            アイテム名です。  
            例：`button`
        callback : Callable
            インタラクションがあった時呼ばれるコルーチン関数です。
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
            "items": self.items
        }


NEW_CORO = """async def new_coro(*args, **kwargs):
    return await self._!!_coro(*args, **kwargs)
self._!!_new_coro = new_coro
del new_coro"""


class Componesy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.views = {}
        self.view = make_view
        if "OnSend" not in self.bot.cogs:
            self.bot.load_extension("rtlib.libs.on_send")
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

            # Viewがまだ作られてないなら作る。
            if view_name not in self.views:
                # discord.ui.Viewのコピーを作る。
                # このコピーからViewのクラスを作っていく。
                NewView = copy(discord.ui.View)

                # rtlib.componesyのために渡されたアイテムリストを一つづつ追加していく。
                for uiitem, coro in items["items"]:
                    # もしメソッドなら
                    if coro.__self__ is None:
                        new_coro = coro
                    else:
                        # もしメソッドならViewに設定できないのでラップする。
                        # この時なぜexecの中に入れる理由：
                        # そうしないとforでとったcoroが使われるはずが、items["items"]の最後のcoroがが使われてしまうから。
                        # 正直なんでそうなるのか対処法もよくわからない誰か教えてくれ。()
                        n = coro.__name__
                        original_coro_name = f"_{n}_coro"
                        setattr(self, original_coro_name, copy(coro))
                        exec(NEW_CORO.replace("!!", n), {"self": self})
                        new_coro_name = f"_{n}_new_coro"
                        new_coro = getattr(self, new_coro_name)
                        delattr(self, new_coro_name)
                    # Viewのコピーに設定する。
                    setattr(NewView, coro.__name__, uiitem(new_coro))
                    del new_coro, coro

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
