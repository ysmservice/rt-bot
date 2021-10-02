# RT.AutoMod - Constants

from enum import Enum


DB = "AutoMod"      # データベースのテーブル名です。
CACHE_TIMEOUT = 30  # スパムをチェックするメッセージのキャッシュの保持時間です。
AM = "[AutoMod]"    # 何かDiscordを操作した際の理由の最初につける文字列です。
MAX_INVITES = 100   # 招待リンク規制チャンネルの設定できる最大数です。
DEFAULT_LEVEL = 2   # デフォルトのスパム検知レベルです。


class DefaultWarn(Enum):
    BAN = 7
    MUTE = 4