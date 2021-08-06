"""# Embeds - 矢印ボタン操作によるEmbedリストを簡単に使うためのエクステンションです。
タイトル通り。  
このエクステンションを読み込む際は`on_send`と`componesy`は自動で読み込まれるので読み込まないでください。  
使用方法はクラス`Embeds`を参照してください。"""

from discord.ext import commands, tasks
import discord

from typing import Optional, Union, Literal, List, Tuple
from asyncio import create_task
from functools import wraps
from time import time

from . import componesy


class EmbedsExpired(Exception):
    pass


def _require_not_expired(function):
    # タイムアウトが切れているならエラー起こすようにするデコレータです。Embedsで使用。
    @wraps(function)
    def new(self, *args, **kwargs):
        if time() - self.last_update > self.timeout:
            self.expired = True
            self.message = None
        if self.expired:
            raise EmbedsExpired(
                "Embedsが期限切れのため操作を実行することができませんでした。")
        return function(self, *args, **kwargs)
    return new


def _is_target(function):
    # 操作可能ユーザーなら実行するようにするデコレータです。Embedsで使用。
    @wraps(function)
    def new(self, view, button, interaction):
        ok = False
        if self.target == "bot_everyone":
            ok = True
        elif self.target == "everyone":
            ok = not interaction.user.bot
        else:
            user_id = (self.target if isinstance(self.target, int)
                       else self.target.id)
            ok = interaction.user.id == user_id
        if ok:
            return function(self, view, button, interaction)
    return new


class Embeds:
    """矢印ボタンでページ切り替えが可能なEmbedのリストであるEmbedsを作るためのクラスです。  
    Embedの編集も`message.edit`からではなくこのクラスから行うことができます。

    Warnings
    --------
    乱用できないようにこれを使うコマンドには`cooldown`を設定しておいた方が無難です。  
    何度も使用されると管理しているEmbedsのリストが増え続け最悪オーバーフローします。(滅多にないだろうけど。)  
    もし「`cooldown`を設定したくないけどオーバーフローが怖いよお。(ポニーテールの少女の声で。)」という人がいるならtimeoutを小さくしましょう。
    
    Parameters
    ----------
    name : str
        Embedsに付ける名前です。  
        ComponesyによるViewに付ける名前のため実行の度に変わる値にしてはいけません！
    target : Union[discord.User, discord.Member, int, Literal["everyone", "bot_everyone"]]
        Embedsを操作することのできるユーザーです。    
        整数を入れた場合はその整数のIDのユーザーのみEmbedsが操作できる対象となります。
        `"everyone"`の場合人間全員となります。  
        `"bot_everyone"`にするとBotを含む全員となります。  
        もし特定の人にしか操作できないようにしたいのならこれを設定しましょう。
    timeout : int, default 60
        ユーザーが操作できなくなるタイムアウトです。  
        この数値を高くする場合は何度もEmbedsのメッセージを送信できないように設定した方が良いです。
    embeds : List[discord.Embed]
        最初のうちに追加しておくEmbedです。

    Attributes
    ----------
    name : str
    target : Union[discord.User, discord.Member, Literal["everyone"]]
    timeout : int
    embeds : List[discord.Embed]
    last_update : float
        最終更新時間です。
    expired : bool
        このEmbedsが期限切れかどうかです。  
        期限切れの場合Embedの追加/削除/編集などができなくなります。
    now : int
        現在表示しているEmbedです。
    message : Union[discord.Message, None]
        Embedsが登録されてるメッセージオブジェクトです。  
        Embedsが登録されているメッセージが送信されるまでまたは期限時れの場合はNoneです。
    items : List[Union[Tuple[Literal[str, Callable, dict], ...], List[str, Callable, dict]]]
        Embedsの操作用のボタンのViewに追加するアイテム一覧です。  
        以下のようなタプルのリストで作ります。  
        `(アイテム名, コールバック, `componesy.View.add_item`に渡すキーワード引数)`  
        もしEmbedsの操作用のボタン以外に何かカスタムでボタンを付け加えたいなどの際はこの属性に手を加えましょう。  
        デフォルトは操作用のボタンであるダッシュ矢印と普通の矢印のボタンとなっています。  
        (デフォルトのボタンラベル：ダッシュ左:`<<`, 左:`<-`, 右:`->`, ダッシュ右:`>>`)"""

    TARGET = Union[discord.User, discord.Member, Literal["everyone"]]

    def __init__(self, name: str, target: TARGET = "everyone",
                 timeout: int = 60, embeds: List[discord.Embed] = []):
        self.name: str = name
        self.target: self.TARGET = target
        self.timeout: int = timeout
        self.embeds: List[discord.Embed] = embeds
        self.last_update: float = time()
        self.expired: bool = False
        self.now: int = 0
        self.message: Union[discord.Message, None] = None
        self.items: List[
            Union[
                Tuple[Literal[str, Callable, dict], ...],
                List[str, Callable, dict]
            ]
        ] = [
            ("button", self._on_dash_left, {"label": "<<"}),
            ("button", self._on_left, {"label": "<-"}),
            ("button", self._on_right, {"label": "->"}),
            ("button", self._on_dash_right, {"label": ">>"})
        ]

    def _on_view(self, view: componesy.View):
        # send時にViewを組み立てる際に呼び出される関数です。
        for item_type, callback, kwargs in self.items:
            view.add_item(item_type, callback, **kwargs)
        return view

    @_is_target
    async def _on_dash_left(self, view, button, interaction):
        self.now -= 2
        if self.now < 0:
            self.now = 0
        await self.update_embed(interaction.message)

    @_is_target
    async def _on_left(self, view, button, interaction):
        if self.now != 0:
            self.now -= 1
            await self.update_embed(interaction.message)

    @_is_target
    async def _on_right(self, view, button, interaction):
        will = self.now + 1
        if will != len(self.embeds):
            self.now = will
            del will
            await self.update_embed(interaction.message)

    @_is_target
    async def _on_dash_right(self, view, button, interaction):
        will = self.now + 2
        if will >= (length := len(self.embeds)):
            will = length - 1
        self.now = will
        del will
        await self.update_embed(interaction.message)

    async def update_embed(self, message: Optional[discord.Message] = None):
        """メッセージを登録されてるEmbedのリストの`Embeds.now`の場所にあるEmbedに更新します。  
        通常は自動でされるのでこれを使うことはないと思います。

        Notes
        -----
        もし`Embeds.now`を手動で変更した場合はこれを実行するべきです。

        Parameters
        ----------
        message : message, optional
            編集対象のメッセージです。"""
        message = self.message if message is None else message
        await message.edit(embed=self.embeds[self.now])
        self.last_update = time()

    @_require_not_expired
    def add_embed(self, embed: discord.Embed) -> None:
        """EmbedsにEmbedを追加します。
        
        Parameters
        ----------
        embed : discord.Embed
            追加するEmbedです。"""
        self.embeds.append(embed)

    @_require_not_expired
    def remove_embed(self, embed: Union[discord.Embed, int]):
        """EmbedsからEmbedを削除します。

        Parameters
        ----------
        embed : discord.Embed
            削除するするEmbedです。  
            もし整数を入れた場合はその番号の場所にあるEmbedが削除されます。"""
        index = embed if isinstance(embed, int) else self.embeds.index(embed)
        self.embeds.pop(index)
        # もし今表示しているEmbedが交換対象と同じかつメッセージ送信済みなら編集を行う。
        if index == self.now and self.message is not None and self.embeds:
            self.now -= 1
            create_task(self.update_embed())

    @_require_not_expired
    def edit_embed(self, target: Union[discord.Embed, int],
                   embed: discord.Embed) -> None:
        """EmbedsにあるEmbedを交換します。

        Notes
        -----
        もしEmbedsが登録されているメッセージが表示しているEmbedが交換対象の場合は、自動でメッセージにあるEmbedが編集されます。

        Parameters
        ----------
        target : Union[discord.Embed, int]
            交換対象のEmbedです。  
            整数を入れた場合その番号の場所にあるEmbedが対象となります。
        embed : discord.Embed
            交換するEmbedです。

        Raises
        ------
        IndexError : 見つからない場合発生します。"""
        index = target if isinstance(target, int) else self.embeds.index(target)
        self.embeds[index] = embed
        # もし今表示しているEmbedが交換対象と同じかつメッセージ送信済みなら編集を行う。
        if self.now == index and self.message is not None:
            create_task(self.update_embed())

    def get_embed(self, index: int) -> discord.Embed:
        """EmbedsにあるEmbedを取得します。
        
        Parameters
        ----------
        index : int
            Embedsのどこの場所にあるEmbedを取得するかです。

        Raises
        ------
        IndexError : 見つからない場合発生します。"""
        return self.embeds[index]

    def _setup(self, mode, t=None, m=None):
        if mode == "init":
            self.last_update = t
            self.message = m
            print(m)
        elif mode == "last_update":
            return self.last_update
        elif mode == "timeout":
            return self.timeout
        else:
            self.message = None
            self.expired = True


class EmbedsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if "OnSend" not in self.bot.cogs:
            self.bot.load_extension("rtlib.ext.on_send")
        self.embeds_queue = []
        self.embeds = {}
        self.bot.cogs["OnSend"].add_event(self._on_send, "on_send")
        self.bot.add_listener(self._on_sended, "on_sended")
        if "Componesy" not in self.bot.cogs:
            self.bot.load_extension("rtlib.ext.componesy")
        self.queue_killer.start()

    @tasks.loop(seconds=5)
    async def queue_killer(self):
        now, delete = time(), []
        # Embedsキューの期限切れの削除をする。
        for embeds, expire in self.embeds_queue:
            if now - expire > 2:
                delete.append((embeds, expire))
        # Embedsの期限切れの削除をする。
        for key in self.embeds:
            if now - self.embeds[key].last_update > self.embeds[key].timeout:
                delete.append(key)
        # 削除キューにあるのを削除する。
        for queue in delete:
            if isinstance(queue, str):
                self.embeds[queue].message = None
                self.embeds[queue].expired = True
                del self.embeds[queue]
            else:
                self.embeds_queue.remove(queue)
        del now, delete

    def cog_unload(self):
        del self.embeds, self.embeds_queue
        self.queue_killer.cancel()

    async def _on_sended(self, message, args, kwargs):
        # send実行後に呼び出される。
        # ここの説明を見る前に下を見よう。
        if (embed := kwargs.pop("embed", False)):
            if (embeds := getattr(embed.__class__, "_rtlib_embeds", False)):
                # IDを作ってEmbedsリストに追加する。
                embedsid = f"{message.channel.id}.{message.id}"
                embeds.last_update = time()
                embeds.message = message
                self.embeds[embedsid] = embeds

    async def _on_send(self, channel, *args, **kwargs):
        # sendが実行された際に呼び出される。
        embeds = kwargs.pop("embeds", None)
        if embeds is not None:
            # もしリスト形式でEmbedが渡されたならそれでEmbedsを作る。
            if isinstance(embeds, list):
                embeds = Embeds(embeds=embeds)
            elif not isinstance(embeds, Embeds):
                raise ValueError("`rtlib.ext.embeds.Embeds`ではないものが入れられました。")
            # Embedsの一番目をキーワード引数のembedに入れる。
            if embeds.embeds == []:
                raise ValueError("送るEmbedがありません。")
            else:
                embed = embeds.embeds[0]
                self.embeds_queue.append((embeds, time()))
                # 送信後にメッセージIDとチャンネルIDと一緒にEmbedsを管理しているしているEmbedsのリストに追加する。
                # それは上の_on_sended内で行われる。これはsend実行後に呼び出される。
                # そこにはキーワード引数が渡されそれのembedの__class__._rtlib_embedsからEmbedsを取得する。。
                # このファイルのルナティックテクニックだよ。（エッヘヘヘヘ）
                embed.__class__._rtlib_embeds = embeds
                kwargs["embed"] = embed
                # 操作用のボタンをrtlib.ext.componesyを使って登録する。
                if not (view := kwargs.get("view")):
                    view = componesy.View(embeds.name, timeout=embeds.timeout)
                view = embeds._on_view(view)
                kwargs["view"] = view
        return args, kwargs

    @commands.command()
    @commands.cooldown(1, 10,)
    async def _embeds_test(self, ctx, *, text):
        embeds = Embeds("_Embeds_test")
        i = 0
        for line in text.splitlines():
            i += 1
            embeds.add_embed(
                discord.Embed(title=f"Embedリスト {i}", description=line)
            )
        await ctx.reply(embeds=embeds)


def setup(bot):
    bot.add_cog(EmbedsCog(bot))