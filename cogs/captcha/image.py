# RT Captcha - Image

from typing import TYPE_CHECKING, Optional, Tuple

import discord

from captcha.image import ImageCaptcha as ImageGenerator
from jishaku.functools import executor_function
from aiofiles.os import remove as aioremove
from aiofiles import open as aioopen
from random import randint

if TYPE_CHECKING:
    from .__init__ import Captcha, Mode


class QueueData:
    mode: "Mode"
    role_id: int
    characters: str
    path: str


def make_random_string(length: int):
    "ランダムな数字の文字列を指定された長さだけ作ります。"
    return "".join(str(randint(0, 9)) for _ in range(length))


class Select(discord.ui.Select):
    "画像認証の画像にある文字を選択するセレクターのクラスです。"

    if TYPE_CHECKING:
        view: "SelectView"

    def __init__(self, *args, **kwargs):
        # 答えの言葉以外の言葉を選択肢に追加する。
        words = []
        for _ in range(9):
            while (
                word := make_random_string(self.view.captcha.password_length)
            ) not in words and word != self.view.characters:
                ...
        for word in words:
            self.add_option(label=word, value=word)
        del words
        # その他設定をする。
        kwargs["custom_id"] = "captcha-image-selector"
        kwargs["placeholder"] = "The string in the image"
        super().__init__(*args, **kwargs)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == self.view.characters:
            if (role := interaction.guild.get_role(
                self.view.captcha.cog.queue \
                    [interaction.guild_id][interaction.user.id][2].role_id
            )):
                try:
                    await interaction.user.add_roles(role)
                except discord.Forbidden:
                    await interaction.response.edit_message("権限がないため役職の付与に失敗しました。")
                else:
                    await interaction.resopnse.edit_message("認証に成功しました。")
                    return await self.view.captcha.cog.remove_queue(
                        interaction.guild_id, interaction.user.id
                    )
            else:
                await interaction.response.edit_message("役職が見つからないため役職の付与ができませんでした。")
        else:
            await interaction.response.edit_message("画像にある文字列と違います。")
        # 認証失敗時には認証用の画像を作り直す。
        await self.view.captcha.update_image(interaction.guild_id, interaction.user.id)


class SelectView(discord.ui.View):
    "画像認証の数字の文字列のセレクターのViewです。"

    def __init__(
        self, captcha: "ImageCaptcha", characters: str, path: str, *args, **kwargs
    ):
        self.captcha, self.characters, self.path = captcha, characters, path
        super().__init__(*args, **kwargs)


class ImageCaptcha(ImageGenerator):
    "画像認証の関数をまとめるためのクラスです。"

    def __init__(
        self, cog: "Captcha", font_path: str = "data/captcha/SourceHanSans-Normal.otf",
        password_length: int = 5
    ):
        self.cog, self.password_length = cog, password_length
        super().__init__(fonts=[font_path])

    @executor_function
    def create_image(self, path: str, characters: Optional[str] = None) -> str:
        "Captcha用の画像を生成します。"
        self.write(
            characters := characters or make_random_string(
                self.password_length
            ), path
        )
        return characters

    BASE_PATH = "data/captcha/"

    def make_path(self, guild_id: int, user_id: int) -> str:
        return f"{self.BASE_PATH}{guild_id}-{user_id}.png"

    async def update_image(self, guild_id: int, member_id: int) -> Tuple[str, str]:
        "認証用の画像を更新します。まだない場合は新規作成します。"
        # 認証用の画像を作りキューにその画像にある文字とパスを保存しておく。
        self.cog.queue[guild_id][member_id][2].path = path = \
            self.make_path(guild_id, member_id)
        self.cog.queue[guild_id][member_id][2].characters = characters = \
            await self.create_image(path)
        # 画像をウェブサーバーに送信する。
        async with self.cog.session as session:
            async with aioopen(path, "rb") as f:
                await session.post(
                    f"{self.cog.bot.get_url()}/captcha/image/post",
                    data=f.read()
                )
            self.cog.print("[Image.Upload]", path)
        self.bot.loop.create_task(aioremove(path))
        return path, characters

    async def on_queue_remove(self, guild_id: int, member_id: int) -> None:
        # キューの削除時にはウェブサーバーに認証用の画像を消すように指示する。
        await self.remove_image(guild_id, member_id)

    async def remove_image(self, guild_id: int, member_id: int) -> None:
        "ウェブサーバーから認証用の画像を削除します。"
        async with self.cog.session as session:
            await session.post(
                f"{self.cog.bot.get_url()}/captcha/image/delete",
                data=self.make_path(guild_id, member_id)
            )

    async def on_captcha(self, interaction: discord.Interaction):
        if (interaction.guild_id in self.cog.queue
                and interaction.user.id in self.cog.queue[interaction.guild_id]):
            # もし既に認証用の画像を作っていたならその画像を使う。
            path, characters = self.cog.queue \
                [interaction.guild_id][interaction.user.id][2].path
        else:
            path, characters = await self.update_image(
                interaction.guild_id, interaction.user.id
            )
        # 返信をする。
        await interaction.response.send_message(
            embed=discord.Embed(
                title={
                    "ja": "画像認証", "en": "Image Captcha"
                },
                description={
                    "ja": "以下の画像にある数字とあてはまるものをメニューから選んでください。",
                    "en": "Please select the number from the menu that matches the number in the image below."
                },
                color=self.cog.bot.Colors.normal
            ), view=SelectView(self, characters, path), ephemeral=True
        )