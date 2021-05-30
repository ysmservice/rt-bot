# RT - Converter

from inspect import signature, _empty
import discord


# コンバーターをコルーチンに設定してその設定済みコルーチンを返す関数。
# これでコードが簡略化する。
def init_converter(coro, ws, data, ctx, *args, **kwargs):
    return Converter(coro, ws, data, ctx, *args, **kwargs).added_coro


# コンバーターを設定するための関数。
class Converter:
    def __init__(self, coro, ws, data, ctx, *args, **kwargs):
        self.ws, self.data, self.ctx = ws, data, ctx
        self.args, self.kwargs = args, kwargs
        self.coro = coro
        self.sig = signature(coro)

    async def _coro(self, ws, data, ctx, *args, **kwargs):
        # コンバーターつきのコルーチン。
        new_args, new_kwargs = [], {}
        # 型変換する。
        parameters = iter(self.sig.parameters)
        for arg in args:
            new_args.append(
                await self.convert(arg, next(parameters).annotation))
        for kwarg in kwargs:
            new_kwargs[kwarg] = await self.convert(
                kwargs[kwarg], next(parameters).annotation)
        await self.coro(ws, data, ctx, *args, **kwargs)

    @property
    def added_coro(self):
        # コンバーターを設定したコルーチンを返す。
        return self._coro(
            self.ws, self.data, self.ctx, *self.args, **self.kwargs)

    async def convert(self, arg, target_type):
        # コンバーターの変換するための関数。
        # もし引数にアノテーションが設定されているなら型変換を行う。
        if target_type is not _empty:
            # discord.pyの型だったらDiscord用のもので変換する。
            # 違う型だったらその型を使って変換を行う。
            # discord.pyの型をtypeに入れるとabc.ABCMetaになるのを利用してdiscord.pyの型か確認する。
            if type(target_type) == type(discord.Member): # noqa
                arg = await self.discord_converter(ctx, arg, target_type)
            else:
                # Example:
                # isinstance(target_type, str), arg == "114514"
                # -> isinstance(returned_arg, int), returned_arg == 114514
                arg = target_type(arg)
        return arg

    async def discord_converter(self, ctx, arg, target_type):
        # 作りかけ
        return arg
