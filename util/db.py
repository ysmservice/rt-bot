"""
freeRT式新データベースマネージャーです。
このマネージャーはdiscord.pyのCogのように使うことができます。
※他のbotには応用しにくい仕組みとなっています。申し訳ありません。
コード例:
```python
from util import db

class Managerrr(db.DBManager):
    def __init__(self, bot):
        self.bot = bot

    async def manager_load(self, cursor):
        # マネージャーが読み込まれた時の特殊関数。
        await cursor.execute("CREATE TABLE user(ID BIGINT, description TEXT, fuga TEXT)")

    async def check_user_id(self, obj: Any):
        return util.isintable(obj) and self.bot.get_user(obj)

    @db.command()
    async def add_user(self, cursor, user: str):
        if not self.check_user_id(user):
            return False
        await cursor.execute("INSERT INTO USERS VALUES(%s, %s, %s)", (int(user), "", ""))

    @db.command(auto=False)
    async def get_user(self, conn, user_id: str):
        if not self.check_user:
            return False
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM USERS WHERE ID=%s", (user_id,))
            return await cursor.fetchone()

class Coooog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.db = await self.bot.add_db_manager(Managerrr(bot))

    @commands.command()
    async def datacheck(self, ctx, id: int):
        result = self.db.get_user.run()
        await ctx.send(result if result else "見つかりませんでした。")
```
"""

from inspect import iscoroutinefunction


class DBManager:
    "データベースマネージャーです。db.command()デコレータが着いたものをコマンドとして扱います。"

    def __init_subclass__(cls):
        return cls  # 未完成

    async def manager_load(self, _):
        pass


def command(**kwargs):
    "これがついた関数をコマンドとして扱うデコレータです。外部から`.run(...)`で呼び出せます。"
    def deco(func):
        if not iscoroutinefunction(func):
            raise ValueError("コマンドはコルーチンである必要があります。")

        async def new_coro(self, *args, **kwargs):  # 未完成
            async with self.bot.pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    return await func(cursor, *args, **kwargs)
        return new_coro
    return deco


async def add_db_manager(bot, manager: DBManager):
    "botにDBManagerを追加します。"
    if not isinstance(manager, DBManager):
        raise ValueError("引数managerはDBManagerのサブクラスである必要があります。")

    if not hasattr(bot, "managers"):
        bot.managers = [manager]
    else:
        bot.managers.append(manager)

    # manager_load関数を実行する。(デフォルトでは何もしない)
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await manager.manager_load(cursor)
