# RT Util - Views

import discord


class TimeoutView(discord.ui.View):
    "タイムアウト時にコンポーネントを使用不可に編集するようにするViewです。"

    def __init__(self, targets: list[str], message: discord.Message, *args, **kwargs):
        self.targets, self.message = targets, message
        super().__init__(*args, **kwargs)

    async def timeout(self):
        edited = False
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.label in self.targets:
                    child.disabled = True
                    edited = True
            elif isinstance(child, discord.ui.Select):
                if child.placeholder in self.targets:
                    child.disabled = True
                    edited = True
        await self.message.edit(view=self)