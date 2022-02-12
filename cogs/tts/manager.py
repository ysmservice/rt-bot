# RT TTS - Manager

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import TTSCog


class Manager:
    def __init__(self, cog: TTSCog, guild: int):
        self.cog, self.guild = cog, guild