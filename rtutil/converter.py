# RT - Converter

from inspect import signature, _empty
import discord


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

        self.builtins = dir(__buildins__)
        self.sig = signature(coro)
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
        await self.coro(ws, data, ctx, *new_args, **new_kwargs)

    @property
    def added_coro(self):
        # コンバーターを設定したコルーチンを返す。
        return self._coro(
            self.ws, self.data, self.ctx, *self.args, **self.kwargs)

    async def convert(self, data, ctx, arg, target_type):
        # コンバーターの変換するための関数。
        # もし引数にアノテーションが設定されているなら型変換を行う。
        if target_type is not _empty:
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
        # 作りかけ
        return arg


class DiscordConverters:
    async def convert_member()
