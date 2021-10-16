# RT.AutoMod - Constants


DB = "AutoMod"      # データベースのテーブル名です。
CACHE_TIMEOUT = 30  # スパムをチェックするメッセージのキャッシュの保持時間です。
AM = "[AutoMod]"    # 何かDiscordを操作した際の理由の最初につける文字列です。
MAX_INVITES = 100   # 招待リンク規制チャンネルの設定できる最大数です。
DEFAULT_LEVEL = 2   # デフォルトのスパム検知レベルです。
DEFAULT_WR = 10     # デフォルトの即抜けBANの秒数範囲です。


class DefaultWarn:
    BAN = 5
    MUTE = 3