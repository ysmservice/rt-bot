# coding: utf-8
# RT.cogs.music - Data Manager ... セーブデータを管理するためのモジュールです。

from rtlib import DatabaseManager


class DataManager(DatabaseManager):

    DB = "Music"

    def __init__(self, db, maxsize: int = 400):
        self.db = db
        self.maxsize = maxsize

    async def init_table(self, cursor) -> None:
        await cursor.create_table(
            self.DB, {
                "UserID": "BIGINT", "Name": "TEXT",
                "Url": "TEXT", "Title": "TEXT"
            }
        )

    async def write_playlist(
        self, cursor, user_id: int, name: str, title: str, url: str
    ) -> None:
        target = {"UserID": user_id, "Url": url, "Title": title, "Name": name}
        if await cursor.exists(self.DB, target):
            raise ValueError("そのプレイリストがありません。")
        elif len(
            [row async for row in cursor.get_datas(
                self.DB, {"UserID": user_id, "Name": name}
            )]
        ) >= self.maxsize:
            await cursor.insert_data(self.DB, target)
        else:
            raise OverflowError("それ以上追加できません。")

    async def delete_playlist_item(
        self, cursor, user_id: int, name: str, title: str
    ) -> None:
        target = {"UserID": user_id, "Name": name, "Title": title}
        if await cursor.exists(self.DB, target):
            await cursor.delete(self.DB, target)

    async def delete_playlist(self, cursor, user_id: int, name: str) -> None:
        target = {"UserID": user_id, "Name": name}
        if await cursor.exists(self.DB, target):
            await cursor.delete(self.DB, target)

    async def read_playlists(
        self, cursor, user_id: int
    ) -> dict:
        data = {}
        async for row in cursor.get_datas(self.DB, {"UserID": user_id}):
            if row:
                if row[1] not in data:
                    data[row[1]] = {}
                data[row[1]][row[3]] = self.get_music(row[2])
        return data
