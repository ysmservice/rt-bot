# RT AutoMod - Cache

from typing import TYPE_CHECKING, Union, Optional, Any, Dict, List

import discord

from time import time

from .modutils import join

if TYPE_CHECKING:
    from .__init__ import AutoMod


class Cache:
    "スパム検知度等のキャッシュ兼ユーザーデータクラスです。"

    # アノテーションをクラスにつけているものはUserDataです。
    warn: float = 0.0

    TIMEOUT = 180
    MAX_SUSPICIOUS = 3

    def __init__(self, cog: "AutoMod", member: discord.Member, data: dict):
        self.guild, self.member, self.cog = member.guild, member, cog
        self.require_save = False
        self.update_time()
        # 初期状態のデータを書き込む。アノテーションがついている変数に書き込まれるべきです。
        for key in data:
            setattr(self, key, data[key])
        # 以下以降スパムチェックに使うキャッシュの部分です。
        self.before: Optional[discord.Message] = None
        self.before_content: Optional[discord.Message] = None
        self.suspicious = 0

    def update_cache(self, message: discord.Message):
        "キャッシュをアップデートします。"
        self.update_timeout()
        before = self.before
        self.before_content = join(self.before)
        self.before = message
        return before

    def update_timeout(self):
        "タイムアウトを更新します。"
        self.checked = time()
        self.timeout = self.checked + self.TIMEOUT

    def keys(self) -> List[str]:
        "このデータクラスにあるキーのリストを返します。"
        return list(self.__annotations__.keys())

    def values(self) -> List[Any]:
        "このデータクラスにある値のリストを返します。"
        return [getattr(self, name) for name in self.keys()]

    def items(self) -> Dict[str, Any]:
        "このデータクラスにあるデータを辞書で返します。"
        return {key: value for key, value in zip(self.keys(), self.values())}

    def update(self, data: "Cache"):
        "このデータクラスにあるデータを更新します。"
        for key, value in data.items():
            setattr(self, key, value)

    def __setattr__(self, key, value):
        if key in self.__annotations__:
            # もしセーブデータが書き換えられたのなら更新が必要とする。
            self.require_save = True
        return super().__setattr__(key, value)