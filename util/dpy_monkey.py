# Free RT - Monkey_Patch, Author: yaakiyu
# これらのコードはd.pyでのみ動作します。

from __future__ import annotations

from discord.ext import commands
import discord

from .webhooks import webhook_send
from .cacher import CacherPool
from .ext import componesy


async def _setup(self, mode: tuple[str, ...] = ()) -> None:
    for name in ("on_send", "on_full_reaction", "on_cog_add"):
        if name in mode or mode == ():
            try:
                await self.load_extension("util.ext." + name)
            except commands.ExtensionAlreadyLoaded:
                pass
    for name in ("dochelp", "rtws", "websocket", "debug", "settings", "lib_data_manager"):
        if name in mode or mode == ():
            try:
                await self.load_extension("util." + name)
            except commands.ExtensionAlreadyLoaded:
                pass
    self.cachers = CacherPool()


# webhook_sendとcomponesyを新しく定義する。
discord.abc.Messageable.webhook_send = webhook_send  # type: ignore
discord.ext.commands.Context.webhook_send = webhook_send  # type: ignore
# componesyに関してはモンキーパッチ脱却予定なのでext.easyからのアクセスは非推奨。
discord.ext.easy = componesy  # type: ignore


default_hybrid_command = commands.hybrid_command


def descriptor_hybrid(default):

    def new_function(*args, **kwargs):
        if not kwargs.get("description", False):
            if kwargs.get("extras", False) and "headding" in kwargs["extras"]:
                kwargs["description"] = kwargs["extras"]["headding"]["ja"]
            else:
                kwargs["description"] = "No description provided."
        return default(*args, **kwargs)

    return new_function


commands.hybrid_command = descriptor_hybrid(commands.hybrid_command)
commands.hybrid_group = descriptor_hybrid(commands.hybrid_group)


def descriptor_sub(default):

    def new_function(self, *args, **kwargs):
        if not kwargs.get("description", False):
            if kwargs.get("extras", False) and "headding" in kwargs["extras"]:
                kwargs["description"] = kwargs["extras"]["headding"]["ja"]
            elif self.description is not None:
                kwargs["description"] = self.description
            else:
                kwargs["description"] = "No description provided."
        return default(self, *args, **kwargs)

    return new_function


commands.HybridGroup.command = descriptor_sub(commands.HybridGroup.command)
commands.HybridGroup.group = descriptor_sub(commands.HybridGroup.group)


async def setup(bot):
    pass
