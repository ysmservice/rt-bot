"""# OnSend
`channel.send(...)`などの実行時に自分の好きなキーワード引数を登録したりする。  
というようなことができるように`on_send`というイベントを作るエクステンションです。  
正確にはdiscord.pyのイベントではありませんので注意。  
なのでこれを使用すれば引数のcontentにeveryoneがあるなら削除したものに引数を置き換えるなどのことが可能です。  
引数から言語名を指定して別の言語にcontentを置き換えるなどが有効的な使用例ですね。

## 使用方法
### 有効化
`bot.load_extension("rtlib.libs.on_send")`で有効にできます。
### イベント追加/削除
追加：`bot.cogs["OnSend"].add_event(コルーチン関数)`
削除：`bot.cogs["OnSend"].remove_event(コルーチン関数)`
### イベントのコルーチン関数
```python
async def on_send(channel, *args, **kwargs):
    return args, kwargs
```

## 使用例
```python
bot.load_extension("rtlib.libs.on_send")

async def on_send(channel, *args, **kwargs):
    # もし送信するのにembedがあればembedのフッターにテキストをつける。
    embed = kwargs.get("embed")
    if embed is not None:
        if embed.footer.text is discord.Embed.Empty:
            embed.set_footer(text="なにかあれば`!help`を実行！")
        kwargs["embed"] = embed
    return args, kwargs

bot.cogs["OnSend"].add_event(on_send)
```"""

from typing import Callable

from discord.ext import commands
import discord

from traceback import print_exc
from copy import copy


class OnSend(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.events = []
        self._dpy_injection()

    def _dpy_injection(self):
        default_send = copy(discord.abc.Messageable.send)

        async def new_send(channel, *args, **kwargs):
            # イベントを実行する。
            for coro in self.events:
                try:
                    args, kwargs = await coro(channel, *args, **kwargs)
                except Exception:
                    print(f"Error on `on_send`, {coro.__name__}:")
                    print_exc()
            return await default_send(
                channel.channel if isinstance(channel, commands.Context) else channel,
                *args, **kwargs
            )
        
        discord.abc.Messageable.send = new_send

    def add_event(self, coro: Callable):
        """send時に呼び出して欲しいコルーチン関数を登録します。  
        登録したコルーチン関数は`送信対象のチャンネル, *args, **kwargs`の引数が渡されます。  
        そして`args, kwargs`を返却しなければなりません。  
        この時`args, kwargs`の値を変えることでsendの引数ができます。
        
        Parameters
        ----------
        coro : Callable
            コルーチン関数です。"""
        self.events.append(coro)

    def remove_event(self, coro: Callable):
        """OnSend.add_eventで登録したコルーチン関数を削除します。
        
        Parameters
        ----------
        coro : Callable
            登録したコルーチン関数です。"""
        self.events.remove(coro)


def setup(bot):
    bot.add_cog(OnSend(bot))