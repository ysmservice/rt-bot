# Free RT Util - Bot

from discord.ext import commands

from aiohttp import ClientSession
from ujson import dumps
from sys import argv

from .dpy_monkey import _setup
from . import mysql_manager as mysql
from .db import add_db_manager, DBManager

from data import data


class RT(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        self.user_prefixes: dict[int, str] = {}
        self.guild_prefixes: dict[int, str] = {}
        # プレフィックスの設定。
        kwargs["command_prefix"] = self.get_prefix
        return super().__init__(*args, **kwargs)

    async def get_prefix(self, m = None):
        pr = data["prefixes"][argv[-1]]
        if not m == None:
            if m.author.id in self.user_prefixes and self.user_prefixes[m.author.id]:
                pr.append(self.user_prefixes[m.author.id])
            if m.guild.id in self.guild_prefixes and self.guild_prefixes[m.guild.id]:
                pr.append(self.guild_prefixes[m.guild.id])
        return pr

    @property
    def session(self) -> ClientSession:
        if self._session.closed:
            # 閉じていたらもう一度定義。
            self._session = ClientSession(loop=self.loop, json_serialize=dumps)
        return self._session

    async def setup_hook(self):
        # 起動中いつでも使えるaiohttp.ClientSessionを作成
        self._session = ClientSession(loop=self.loop, json_serialize=dumps)
        # 起動中だと教えられるようにするためのコグを読み込む
        await self.load_extension("cogs._first")
        # jishakuを読み込む
        await self.load_extension("jishaku")
        self.mysql = self.data["mysql"] = mysql.MySQLManager(
            loop=self.loop,
            **self.secret["mysql"],
            pool=True,
            minsize=1,
            maxsize=500 if self.test else 1000000,
            autocommit=True
        )  # maxsizeはテスト用では500、本番環境では100万になっている
        self.pool = self.mysql.pool  # bot.mysql.pool のエイリアス

    def print(self, *args, **kwargs) -> None:
        "[RT log]と色の装飾を加えてprintをします。"
        temp = [*args]
        if len(args) >= 1 and args[0].startswith("[") and args[0].endswith("]"):
            temp[0] = f"\033[93m{args[0]}\033[0m"
        if len(args) >= 2 and str(args[1]).startswith("[") and str(args[1]).endswith("]"):
            temp[1] = f"\033[95m{str(args[1])}\033[0m"
        return print("\033[32m[RT log]\033[0m", *temp, **kwargs)

    def get_ip(self) -> str:
        return "localhost" if self.test else "free-rt.com:8081"

    def get_url(self) -> str:
        return f"http://{self.get_ip()}"

    async def close(self) -> None:
        "botが終了するときの動作。on_closeが呼ばれる。"
        self.print("Closing...")
        self.dispatch("close", self.loop)
        await super().close()
        self.print("Bye")

    def get_website_url(self) -> str:
        return "http://localhost/" if self.test else "https://free-rt.com/"

    async def add_cog(self, cog: commands.Cog, override: bool = True, **kwargs):
        "add_cogの拡張。overrideがデフォルトでTrueなのと、OnCogAddに関する動作をする。"
        if "OnCogAdd" in self.cogs:
            self.cogs["OnCogAdd"]._add_cog(cog, **kwargs)
        return await super().add_cog(cog, override=override, **kwargs)

    async def remove_cog(self, cog_name: str):
        "remove_cogの拡張。OnCogAddに関する動作をする。"
        if "OnCogAdd" in self.cogs:
            self.cogs["OnCogAdd"]._remove_cog(cog_name)
        return await super().remove_cog(cog_name)

    async def setup(self, mode: tuple = ()) -> None:
        "utilにある拡張cogをすべてもしくは指定されたものだけ読み込みます。"
        return await _setup(self, mode)

    async def add_db_manager(self, manager: DBManager) -> DBManager:
        return await add_db_manager(self, manager)
