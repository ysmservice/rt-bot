# coding: utf-8
# RT.cogs.music - Data Manager ... セーブデータを管理するためのモジュールです。

from .cogs.classes import MusicRawDataForJson
from rtlib import DatabaseManager


class DataManager(DatabaseManager):

    DB = "Music"

    def __init__(self, db, max_music: int = 800, max_playlist: int = 10):
        self.db = db
        self.max_music = max_music
        self.max_playlist = max_playlist

    async def _get_playlists(self, cursor, target):
        data = []
        async for row in cursor.get_datas(self.DB, target):
            if row and row[1] not in data:
                data.append(row[1])
        return data

    async def init_table(self, cursor) -> None:
        await cursor.create_table(
            self.DB, {
                "UserID": "BIGINT", "Name": "TEXT",
                "Data": "JSON"
            }
        )

    async def get_playlists(self, cursor, user_id: int, extras: dict = {}) -> list:
        target = {"UserID": user_id}
        target.update(extras)
        return await self._get_playlists(cursor, target)

    async def make_playlist(
        self, cursor, user_id: int, name: str
    ) -> None:
        target = {"UserID": user_id, "Name": name, "Data": {}}
        if await cursor.exists(self.DB, target):
            raise ValueError("そのプレイリストは既に存在します。")
        elif len(
            await self._get_playlists(cursor, {"UserID": user_id})
        ) == self.max_playlist:
            raise OverflowError("これ以上プレイリストを作ることはできません。")
        target["Data"] = {}
        await cursor.insert_data(self.DB, target)

    async def write_playlist(
        self, cursor, user_id: int, name: str, data: MusicRawDataForJson
    ) -> None:
        target = {"UserID": user_id, "Name": name}
        if not await cursor.exists(self.DB, target):
            raise ValueError("そのプレイリストは存在しません。")
        elif len(
            [row async for row in cursor.get_datas(
                self.DB, target
            )]
        ) - 1 >= self.max_music:
            raise OverflowError("それ以上追加できません。")
        else:
            target["Data"] = data
            await cursor.insert_data(self.DB, target)

    async def delete_playlist_item(
        self, cursor, user_id: int, name: str, data: MusicRawDataForJson
    ) -> None:
        target = {"UserID": user_id, "Name": name, "Data": data}
        if await cursor.exists(self.DB, target):
            await cursor.delete(self.DB, target)
        else:
            raise ValueError("その曲は登録されていません。またはプレイリストが存在しません。")

    async def delete_playlist(self, cursor, user_id: int, name: str) -> None:
        target = {"UserID": user_id, "Name": name}
        if await cursor.exists(self.DB, target):
            await cursor.delete(self.DB, target)
        else:
            raise ValueError("そのプレイリストがありません。")

    async def read_playlists(
        self, cursor, user_id: int, name: str = None
    ) -> dict:
        data = {}
        target = {"UserID": user_id}
        if name is not None:
            target["Name"] = name
        async for row in cursor.get_datas(self.DB, target):
            if row and len(row) > 2:
                if row[1] not in data:
                    data[row[1]] = []
                data[row[1]].append(row[2])
        return data
