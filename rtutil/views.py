# RT Util - Views

import discord


class TimeoutView(discord.ui.View):
    "タイムアウト時にコンポーネントを使用不可に編集するようにするViewです。"

    message: discord.Message

    def __init__(self, targets: list[str], *args, **kwargs):
        self.targets = targets
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
