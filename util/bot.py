# Free RT Util - Bot

from discord.ext import commands

from .dpy_monkey import _setup


class RT(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        return super().__init__(*args, **kwargs)

    def print(self, *args, **kwargs) -> None:
        temp = [*args]
        if len(args) >= 1 and args[0].startswith("[") and args[0].endswith("]"):
            temp[0] = f"\033[93m{args[0]}\033[0m"
        if len(args) >= 2 and args[1].startswith("[") and args[1].endswith("]"):
            temp[1] = f"\033[95m{args[0]}\033[0m"
        return print("\033[32m[RT log]\033[0m", *temp, **kwargs)

    def get_ip(self) -> str:
        return "localhost" if self.test else "60.158.90.139"

    def get_url(self) -> str:
        return f"http://{self.get_ip()}"

    async def close(self) -> None:
        self.print("Closing...")
        self.dispatch("close", self.loop)
        await super().close()
        self.print("Bye")

    def get_website_url(self) -> str:
        return "http://localhost/" if self.test else "https://free-rt.com/"

    async def add_cog(self, *args, override: bool = True, **kwargs):
        return await super().add_cog(*args, override=override, **kwargs)

    async def setup(self, mode=None) -> None:
        "utilにある拡張cogをすべてもしくは指定されたものだけ読み込みます。"
        return await _setup(self, mode)
