# cogsファイルマップ
## bot_general.py
* ping
* info
* on_command_error (イベント)
* ステータスアップデート (ループ)
### on_command_errorでのToDo
* 権限が足りない際には足りない権限の名前を表示する。
* RT専用のエラーメッセージのクラスのエラーハンドリングをする。(`commands.errors.CommandError`)
* 400エラーの場合はヘルプに誘導する。
## database.py
* データベースを操作するためのコマンドであるdatabase
## help.py
ヘルプ
## language.py
* 別言語に交換するためのもの
* 言語設定コマンド
## news.py <まだウェブAPIができてない>
* ニュース
## poll.py
* 投票パネル
## role.py
* 役職パネル