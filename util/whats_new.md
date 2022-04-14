# What's new
util統合による更新ログみたいなものです。

## 機能移動
utilへの統合により以下の関数の名前が変更になりました。
* rtutil.check_int -> rtutil.isintable
* rtutil.similer -> rtutil.olds.similer
* rtutil.has_roles -> rtutil.has_any_roles
* rtutil.role2obj -> rtutil.olds.role2obj
* rtutil.get_webhook -> rtutil.olds.get_webhook
* rtutil.clean_content -> rtutil.olds.clean_content
* rtutil.converters.xxx
    -> それぞれのコンバータが独立。  
    Members -> rtutil.MembersConverter  
    TextChannels -> rtutil.TextChannelsConverter  
    VoiceChannels -> rtutil.VoiceChannelsConverter  
    Roles -> rtutil.RolesConverter
* rtutil.markord.xxx -> それぞれ独立(関数名も変更、詳細はmarkdowns.py)
* rtutil.Minesweeper -> rtutil.MineSweeper (内容が変更、詳細はminesweeper.py)
* rtutil.securl -> 変更なし
* rtutil.views.TimeoutView -> rtutil.TimeoutView