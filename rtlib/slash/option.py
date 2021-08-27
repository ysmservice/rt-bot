# rtlib.slash - Options

from typing import Union, Optional, Any, List, Tuple
from .types import get_option_type, ApplicationCommandOption


Choice = Union[
    List[Union[str, Union[str, int, float]]],
    Tuple[str, Union[str, int, float]]
]
Choices = Union[List[Choice], Tuple[Choice, ...]]


class CanNotUseChoice(Exception):
    pass


class Option:
    def __init__(
            self, type_: object, name: str, description: str,
            required: bool = True, choices: Optional[Choices] = None,
            value: Any = None):
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
        cls.options = [cls.from_dictionary(option_data)
                       for data in data.get("options", ())]
        return cls(
            data["type"], data["name"], data.get("description", "..."),
            data.get("required", False),
            [(data["name"], data["value"]) for data in data.get("choices", ())],
            data.get("value")
        )