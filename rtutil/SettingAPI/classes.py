# rtutil SettingAPI - Classes

from typing import (Type, Literal, Optional, Union, Iterator,
                    Any, List, Tuple, Dict, Callable, Coroutine)
from sanic import exceptions
from copy import copy

from discord.ext import commands
import discord


SettingType = Literal["guild", "user"]
ModeType = Literal["write", "read"]
IGNORE_VALUES = ("ITEM_TYPE", "display_name", "on_init", "name")


def get_bylang(data: Union[str, Dict[str, str]], lang: str) -> str:
    if isinstance(data, dict):
        return data.get(lang, data["ja"])
    else:
        return data


class Context:
    def __init__(self, mode: ModeType, author: Type[discord.abc.User]):
        self.mode: ModeType = mode
        self.author: Type[discord.abc.User] = author
        self.guild: Union[discord.Guild, None] = getattr(author, "guild", None)


class SettingItem:
    def __init__(self, name: str, display_name: Union[str, Dict[str, str]],
                 *args, **kwargs):
        self.name = name
        self.display_name = display_name
        if (on_init := getattr(self, "on_init", None)):
            on_init(*args, **kwargs)


class SettingData:
    def __init__(self, setting_type: SettingType,
                 description: Union[str, Dict[str, str]],
                 callback: Callable[[Any], Coroutine],
                 *args, permissions: List[str] = [], **kwargs):
        self.description: str = description
        self.permissions: List[str] = permissions
        self.callback: Callable[[Context, SettingItem]] = callback
        self.setting_type: Literal["guild", "user"] = setting_type
        self.data: List[Type[SettingItem]] = args

    async def run_callback(
            self, *args, cog: Union[None, commands.Cog] = None
            ) -> Optional[Type[SettingItem]]:
        return await self.callback(*(([cog] if cog else []) + list(args)))

    async def get_dictionary(
                self, cog: Union[None, commands.Cog], lang: str,
                mode: ModeType, member: discord.Member
            ) -> List[Tuple[str, Dict[str, Union[str, dict]]]]:
        return [(item, {
            "item_type": item.ITEM_TYPE,
            "display_name": get_bylang(item.display_name, lang),
            item.ITEM_TYPE: {
                name: getattr(item, name)
                for name in dir(
                    await self.run_callback(
                        Context(mode, member), copy(item),
                        cog=cog
                    )
                )
                if name not in IGNORE_VALUES
                    and not name.startswith("_")
            }
        }) for item in self.data]

    async def update_setting(
            self, cog: Union[None, commands.Cog], item_name: str,
            data: dict, member: discord.Member) -> None:
        for item in self.data:
            if item.name == item_name:
                item = copy(item)
                for key in data[data["item_type"]]:
                    if key not in IGNORE_VALUES:
                        setattr(item, key, data[data["item_type"]][key])
                await self.run_callback(
                    Context("write", member), item,
                    cog=cog
                )
                break
        else:
            raise exceptions.SanicException(
                message="(更新する設定が)ないです。",
                status_code=404
            )


class TextBox(SettingItem):

    ITEM_TYPE = "text"

    def on_init(self, text: str, multiple_line: bool = False):
        self.text: str = text
        self.multiple_line: bool = multiple_line


class CheckBox(SettingItem):

    ITEM_TYPE = "check"

    def on_init(self, checked: bool):
        self.checked: bool = checked


class RadioButton(SettingItem):

    ITEM_TYPE = "radios"

    def on_init(self, data: dict):
        for key in data:
            setattr(self, key, data[key])


class ListBox(SettingItem):

    ITEM_TYPE = "list"

    def on_init(self, index: int, texts: List[str]):
        self.index: int = index
        self.texts: List[str] = texts
