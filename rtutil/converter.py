# RT - Converter

from inspect import signature
import asyncio


class Converter:
    def converter(self, coro):
        self.coro = coro
        self.sig = signature(coro)

    async def _coro(ws, data, ctx, *args, **kwargs):
        for arg in args:
            await self.convert(arg)
        await coro(ws, data, ctx, *args, **kwargs)

    def convert(self, coro):
        
