# RT TTS - Data Manager

from rtlib import mysql


MySQLManager, Cursor = mysql.MySQLManager, mysql.Cursor


class DataManager:
    def __init__(self, db: MySQLManager):
        self.db: MySQLManager = db

    async def init_table(self) -> None:
        """テーブルの初期状態を作ります。"""
        columns = {
            "type": "TEXT",
            "id": "BIGINT",
            "content": "TEXT"
        }
        async with self.db.get_cursor() as cursor:
            await cursor.create_table("tts", columns)

    async def check_exists(self, cursor: Cursor, type_: str, some_id: int):
        """指定されたtypeでsome_idのデータがあるか確認します。

        Parameters
        ----------
        cursor : Cursor
            カーソルです。
        type_ : str
            データのタイプです。
        some_id : int
            IDです。"""
        return await cursor.exists("tts", {"type": type_, "id": some_id})

    async def write_voice(self, user_id: int, name: str) -> None:
        """指定したユーザーIDに声の名前を設定します。

        Parameters
        ----------
        user_id : int
            対象のユーザーIDです。
        name : str
            声の名前です。"""
        async with self.db.get_cursor() as cursor:
            if await self.check_exists(cursor, "voice", user_id):
                await cursor.update_data(
                    "tts", {"content": name}, {"type": "voice", "id": user_id}
                )
            else:
                await cursor.insert_data(
                    "tts", {"type": "voice", "id": user_id, "content": name}
                )

    async def read_voice(self, user_id: int) -> str:
        """指定したユーザーIDの声を取得します。

        Parameters
        ----------
        usre_id : int
            対象のユーザーIDです。"""
        async with self.db.get_cursor() as cursor:
            if await self.check_exists(cursor, "voice", user_id):
                row = await cursor.get_data(
                    "tts", {"type": "voice", "id": user_id}
                )
                if row:
                    return row[-1]
                else:
                    return "mei"
            else:
                return "mei"

    async def write_dictionary(self, data: dict, guild_id: int) -> None:
        """辞書を指定したIDと一緒に保存します。

        Parameters
        ----------
        data : dict
            保存する辞書データです。
        guild_id : int
            サーバーのIDです。"""
        async with self.db.get_cursor() as cursor:
            if await self.check_exists(cursor, "dictionary", guild_id):
                await cursor.update_data(
                    "tts", {"content": data}, {"type": "dictionary", "id": guild_id}
                )
            else:
                await cursor.insert_data(
                    "tts", {"type": "dictionary", "id": guild_id, "content": data}
                )

    async def read_dictionary(self, guild_id: int) -> dict:
        """指定したIDと一緒に保存されてる辞書を読み込みます。

        Parameters
        ----------
        guild_id : int
            サーバーIDです。"""
        async with self.db.get_cursor() as cursor:
            if await self.check_exists(cursor, "dictionary", guild_id):
                rows = await cursor.get_data("tts", {"type": "dictionary", "id": guild_id})
                if rows:
                    return rows[-1]
                else:
                    return {}
            else:
                return {}

    async def write_routine_mode(self, user_id: int, b: bool) -> None:
        """指定したユーザーIDのネタモードの切り替えをします。"""
        async with self.db.get_cursor() as cursor:
            if await self.check_exists(cursor, "routine", user_id):
                await cursor.update_data(
                    "tts", {"content": str(int(b))},
                    {"type": "routine", "id": user_id}
                )
            else:
                await cursor.insert_data(
                    "tts", {"content": str(int(b)), "type": "routine",
                            "id": user_id}
                )

    async def read_routine_mode(self, user_id: int) -> bool:
        """指定したユーザーのIDのネタモードを調べます。"""
        async with self.db.get_cursor() as cursor:
            if await self.check_exists(cursor, "routine", user_id):
                row = await cursor.get_data(
                    "tts", {"type": "routine", "id": user_id}
                )
                if row:
                    return bool(int(row[-1]))
                else:
                    return False
            else:
                return False

    async def write_routine(self, user_id: int, data: dict) -> None:
        async with self.db.get_cursor() as cursor:
            if await self.check_exists(cursor, "custom", user_id):
                await cursor.update_data(
                    "tts", {"content": data},
                    {"type": "custom", "id": user_id}
                )
            else:
                await cursor.insert_data(
                    "tts", {"content": data, "type": "custom",
                            "id": user_id}
                )

    async def read_routine(self, user_id: int) -> dict:
        async with self.db.get_cursor() as cursor:
            if await self.check_exists(cursor, "custom", user_id):
                row = await cursor.get_data(
                    "tts", {"type": "custom", "id": user_id}
                )
                if row:
                    return row[-1]
                else:
                    return {}
            else:
                return {}
