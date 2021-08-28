# rtutil.SettingAPI - Utils

from typing import Any, List

from .classes import ListBox


def make_list(members: List[Any], name: str, default: Any) -> ListBox:
    return ListBox(
        members.index(default),
        [getattr(member, name) for member in members]
    )