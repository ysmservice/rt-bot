# rtlib.slash - Options

from .types import get_option_type, ApplicationCommandOption
from typing import Union, Optional, Any, List, Tuple

from discord.ext import commands
import inspect


Choice = Union[
    List[Union[str, Union[str, int, float]]],
    Tuple[str, Union[str, int, float]]
]
Choices = Union[List[Choice], Tuple[Choice, ...]]


class CanNotUseChoice(Exception):
    pass


class Option(commands.Converter):
    def __init__(
            self, type_: object, name: str, description: str,
            required: bool = True, choices: Optional[Choices] = None,
            value: Any = None):
        self.annotation = type_
        self.type: int = get_option_type(type_)
        self.name: str = name
        self.description: str = description
        self.choices: Optional[Choices] = None
        if choices and self.type in (3, 4, 10):
            self.choices = choices
        elif choices:
            raise CanNotUseChoice(
                "Choiceはオプションの種類が文字列、整数または少数でないと使えません。"
            )
        self.required: bool = required
        self.options = []
        self.value = value

    @classmethod
    def from_dictionary(cls, data: ApplicationCommandOption) -> object:
        new = cls(
            data["type"], data["name"], data.get("description", "..."),
            data.get("required", False),
            [(data["name"], data["value"]) for data in data.get("choices", ())],
            data.get("value")
        )
        new.options = [cls.from_dictionary(data)
                       for data in data.get("options", ())]
        return new

    def __str__(self):
        return f"<Option {self.name} <Type {self.type}> <Options {' '.join(str(option) for option in self.options)}>>"

    async def convert(self, ctx, *args, **kwargs):
        if inspect.isbuiltin(self.annotation):
            return self.annotation(*args, **kwargs)
        else:
            try:
                func = getattr(
                    commands.converter, f"{self.annotation.__name__}Converter"
                )
            except AttributeError:
                if hasattr(self.annotation, "convert"):
                    await self.annotation.convert(
                        None, ctx, *args, **kwargs
                    )
                else:
                    coro = self.annotation(*args, **kwargs)
                    if inspect.iscoroutinefunction(self.annotation):
                        return await coro
                    else:
                        return coro
            else:
                return await func().convert(ctx, *args, **kwargs)