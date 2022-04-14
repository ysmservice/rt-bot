# What's new
util統合による更新ログみたいなものです。

## 機能移動
utilへの統合により以下の関数の名前が変更になりました。

### rtutil
* rtutil.check_int -> util.isintable
* rtutil.similer -> util.olds.similer
* rtutil.has_roles -> util.has_any_roles
* rtutil.role2obj -> util.olds.role2obj
* rtutil.get_webhook -> util.olds.get_webhook
* rtutil.clean_content -> util.olds.clean_content
* rtutil.converters.xxx
    -> それぞれのコンバータが独立。  
    Members -> util.MembersConverter  
    TextChannels -> util.TextChannelsConverter  
    VoiceChannels -> util.VoiceChannelsConverter  
    Roles -> util.RolesConverter
* rtutil.markord.xxx -> それぞれ独立(関数名も変更、詳細はmarkdowns.py)
* rtutil.Minesweeper -> util.MineSweeper (内容が変更、詳細はminesweeper.py)
* rtutil.securl -> 変更なし
* rtutil.views.TimeoutView -> util.TimeoutView

### rtlib
* 