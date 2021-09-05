# rtutil.SettingAPI - Utils

from typing import Any, List

from .classes import ListBox


def make_list(
    display_name: str, description: Any, members: List[Any],
    name: str, default: Any
) -> ListBox:
    return ListBox(
        display_name, description,
        members.index(default),
        [getattr(member, name, member if isinstance(member, str) else name)
         for member in members]
    )