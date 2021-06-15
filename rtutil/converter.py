# RT - Converter

import inspect
import discord
import asyncio
from .utils import cc_int, get


# コンバーターをコルーチンに設定してその設定済みコルーチンを返す関数。
# これでコードが簡略化する。
def add_converter(coro, ws, data, ctx, *args, **kwargs):
    return Converter(coro, ws, data, ctx, *args, **kwargs).added_coro


# コンバーターを設定するための関数。
class Converter:
    def __init__(self, coro, ws, data, ctx, *args, **kwargs):
        self.ws, self.data, self.ctx = ws, data, ctx
        self.args, self.kwargs = args, kwargs
        self.coro = coro

        self.builtins = dir(__builtins__)
        self.sig = inspect.signature(coro)
        self.another_convert = {
            bool: self.convert_bool
        }

    async def _coro(self, ws, data, ctx, *args, **kwargs):
        # コンバーターつきのコルーチン。
        new_args, new_kwargs = [], {}
        # 引数のシグネチャを取得する。
        parameters = iter(self.sig.parameters)
        for _ in range(5):
            # コマンドに書かれている引数になるまで引数リストを取り出しとく。
            if next(parameters) == "ctx":
                break
        # 引数を変換する。
        for arg in args:
            new_args.append(
                await self.convert(
                    data, ctx, arg,
                    self.sig.parameters[next(parameters)].annotation
                )
            )
        for kwarg in kwargs:
            new_kwargs[kwarg] = await self.convert(
                data, ctx, kwargs[kwarg],
                self.sig.parameters[next(parameters)].annotation
            )
        await self.coro(data, ctx, *new_args, **new_kwargs)

    @property
    def added_coro(self):
        # コンバーターを設定したコルーチンを返す。
        return self._coro(
            self.data, self.ctx, *self.args, **self.kwargs)

    async def convert(self, data, ctx, arg, target_type):
        # コンバーターの変換するための関数。
        # もし引数にアノテーションが設定されているなら型変換を行う。
        if not isinstance(target_type, inspect.empty):
            # discord.pyの型だったらDiscord用のもので変換する。
            # 違う型だったらその型を使って変換を行う。
            # discord.pyの型をtypeに入れるとabc.ABCMetaになるのを利用してdiscord.pyの型か確認する。
            if type(target_type) == type(discord.Member): # noqa
                arg = await self.discord_converter(data, ctx, arg, target_type)
            else:
                # Example:
                # isinstance(target_type, str), arg == "114514"
                # -> isinstance(returned_arg, int), returned_arg == 114514
                if target_type in self.another_convert:
                    arg = self.another_convert(arg)
                elif str(target_type)[8:-2] in self.builtins:
                    arg = target_type(arg)
                else:
                    # custom converter
                    if str(target_type).startswith("<function"):
                        if asyncio.iscoroutine(target_type):
                            arg = await target_type(data, ctx, arg)
                        else:
                            arg = target_type(data, ctx, arg)
        return arg

    def convert_bool(self, arg) -> bool:
        if arg.lower() in ("true", "on", "1", "activate"):
            return True
        else:
            return False

    async def discord_converter(self, data, ctx, arg, target_type):
        if isinstance(target_type, discord.Member):
            arg = self.convert_member(data, ctx, arg)
        elif isinstance(target_type, discord.Role):
            arg = self.convert_role(data, ctx, arg)
        elif isinstance(target_type, discord.TextChannel):
            arg = self.convert_text_channel(data, ctx, arg)
        elif isinstance(target_type, discord.VoiceChannel):
            arg = self.convert_voice_channel(data, ctx, arg)
        return arg

    async def convert_some_mention(self, data, ctx, arg, key, exts):
        # メンション用のコンバーター。
        # ここで登場するcc_intとgetはrtutil/utils.pyにある。
        _id = cc_int(arg)
        if _id or ("<" == arg[0] and ">" in arg[-1]):
            if not _id:
                # もしIDじゃないなくメンションっぽかったらIDを取り出す。
                _id = arg.replace("<", "").replace(">", "")
                for ext in exts:
                    _id = _id.replace(ext, "")
                _id = int(_id)
            return get(data["guild"][key], id=_id)
        else:
            # 名前から取り出す。
            return get(data["guild"][key], name=arg)

    async def convert_member(self, data, ctx, arg):
        return self.convert_some_mention(
            data, ctx, arg, "members", ("!",))

    async def convert_role(self, data, ctx, arg):
        return self.convert_some_mention(
            data, ctx, arg, "roles", ("@", "&"))

    async def convert_text_channel(self, data, ctx, arg):
        return self.convert_some_mention(
            data, ctx, arg, "text_channels", ("#",))

    async def convert_voice_channel(self, data, ctx, arg):
        return self.convert_some_mention(
            data, ctx, arg, "voice_channels", ())
