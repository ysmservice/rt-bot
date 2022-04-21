# RT - Monky_Patch, Author: yaakiyu
# これらのコードはd.pyでのみ動作します。

from __future__ import annotations

from discord.ext import commands
from discord import app_commands
import discord

##  ここからスラッシュ関連
# コマンドを標準でハイブリッドにする。
commands.command = commands.hybrid_command
commands.group = commands.hybrid_group


# add_cogの際にデフォルトでオーバーライドするようにする。
original_add_cog = commands.Bot.add_cog

async def _new(self, *args, override: bool = True, **kwargs) -> None:
    return await original_add_cog(*args, override=override, **kwargs)

commands.Bot.add_cog = _new


# コマンドのextrasのheaddingをshort-descriptionに登録する。


# on_full_readyが呼ばれた時にtreeをsyncする。

