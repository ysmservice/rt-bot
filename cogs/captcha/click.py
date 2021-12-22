# RT Captcha - Click

from typing import TYPE_CHECKING

from discord import Interaction

from .image import add_roles

if TYPE_CHECKING:
    from .__init__ import Captcha


class ClickCaptcha:
    def __init__(self, cog: "Captcha"):
        self.cog = cog

    async def on_captcha(self, interaction: Interaction):
        # クリックするだけの認証方式のため付与するだけ。
        return await add_roles(self, interaction)