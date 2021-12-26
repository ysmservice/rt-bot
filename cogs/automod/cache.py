# RT AutoMod - Cache

from typing import TYPE_CHECKING, Union, Optional, Any, Dict, List

import discord

from time import time

if TYPE_CHECKING:
    from .__init__ import AutoMod


class Cache:
    "スパム検知度等のキャッシュ兼ユーザーデータクラスです。"

    # アノテーションをクラスにつけているものはGuildDataです。
    warn: float = 0.0

    TIMEOUT = 180

    def __init__(self, cog: "AutoMod", member: discord.Member, data: dict):
        self.guild, self.member, self.cog = member.guild, member, cog
        self.timeout, self.require_save = time() + self.TIMEOUT, False
        # 初期状態のデータを書き込む。アノテーションがついている変数に書き込まれるべきです。
        for key in data:
            setattr(self, key, data[key])

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