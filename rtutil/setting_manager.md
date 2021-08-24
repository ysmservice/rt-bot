# SettingManager API 説明
ウェブでも設定ができるように簡単にするためのシステムの設定取得/更新のAPIの説明です。

## OAuthについて
これは本当はSettingManagerではないのですが一様説明を記載する。  
RTは一度認証するとクッキーに暗号化したユーザーIDとユーザー名をメモします。  
なのでこのAPIを使用する際はクッキーにRTで作られたクッキーが存在している必要があります。  
`session=ユーザーID&ユーザー名を暗号化した文字列`

## 設定項目
設定項目とはテキストボックスやラジオボタンなどのことです。  
API仕様はこの下にあります。
### テキストボックス
設定名は`text`です。
```js
{
    "multiple_line": bool,
    "text": "文字列"
}
```
> `文字列`

とありますが、ここは取得時は現在設定されている値が入ります。  
もちろん設定更新後もここに値を入れてPOSTします。
### チェックボックス
設定名は`check`です。
```js
{
    "checked": bool,
}
```
> `checked`

ここは取得時は現在設定されている値が入ります。  
もちろん設定更新後もここに値を入れてPOSTをします。
### ラジオボタン
設定名は`radios`です。
```js
{
    "ラジオボタン名": bool
}
```
> `radios`

ここの中にある辞書はキーがラジオボタンの名前で値がチェックされてるかされてないかです。  
ここは取得時は現在設定されている値が入ります。  
もちろん設定更新後もここに値を入れてPOSTをします。
### リストボックス
設定名は`list`です。
```js
{
    "index": int, // 現在リストの中で選択されている場所。
    "texts": [str, ...] // リストにある文字列のリスト。
}
```
> `index`

ここは取得時は現在設定されている値が入ります。  
もちろん設定更新後もここに値を入れてPOSTをします。

## URI
### /api/settings/<mode> GET
現在ログインしているユーザーが持っている権限で設定可能な設定のリストを取得します。  
`<mode>`にはサーバー設定である`guild`またはユーザー個人の設定である`user`を入れることができます。  
`<mode>`が`user`の場合は権限どうこうのことはないです。
#### modeがguildの場合
取得に成功すれば以下のようなjsonが帰ってきます。
```js
{
    "status": "ok",
    "settings": {
        "サーバーID": {
            "name": "サーバー名",
            "icon": "サーバーアイコンのURL",
            "commands": {
                "コマンド名/設定名": {
                    "description": "コマンド/設定の説明",
                    "items": {
                        "設定項目名": {
                            "item_type": "設定項目の種類",
                            "display_name": "ウェブで表示する設定項目の名前"
                            "item_typeに入っていた名前": {
			                    // その設定に既に書き込まれている内容。
				                // ここは上の設定の項目の説明でだしたjsonが入る。
	            		    }
                        }
                    }
                }
            }
        }
    }
}
```
#### modeがuserの場合
取得に成功すれば以下のようなjsonが帰ってきます。
```js
{
    "status": "ok",
    "settings": {
        "コマンド名/設定名": {
    	    "description": "コマンド/設定の説明",
    	    "items": {
    	        "設定項目名": {
    		        "item_type": "設定項目の種類",
    		        "display_name": "ウェブで表示する設定項目の名前"
    		        "設定項目の種類": {
    		            // その設定に既に書き込まれている内容。
        		        // ここは上の設定の項目の説明でだしたjsonが入る。
                    }
    	 	    }
    	    }
	    }
    }
}
```

### /api/settings/update/guild/<guild_id> POST
`<guild_id>`のサーバーの設定を更新します。  
このAPIを叩く際にログインしているユーザーの権限で設定更新を試みます。  
(ですが上のAPIで取得した設定一覧はユーザーが設定更新に必要な権限を持っている設定のみなので気にする必要はないです。)  
以下のようにデータをPOSTしてください。
```js
{
    "コマンド名/設定名": {
        "設定項目名": {
    	    "item_type": "設定項目の種類",
	        "設定項目の種類": // 上のGETで取得した設定項目で設定更新時に変更すべき場所を変更した後の辞書をここに入れればいい。
	    }
    }
}
```
### /api/settings/update/user POST
このAPIを叩く際にログインしているユーザーの個人設定を更新します。  
POSTするデータの形式は上と同じです。

## バックエンド
以下のようにコグ内でコマンドのextrasから設定を登録することができます。
```python
from rtutil import SettingManager

# ...

class Cog(commands.Cog):
    #...

    async def callback(self, ctx, item):
        print(ctx.mode, item.name, ctx.author.name,
              getattr(ctx.guild, "id", "サーバーはなし"))
        return item

    @commands.command(
        extras={
            "setting": SettingData(
                "guild", {"ja": "テスト", "en": "test"}, callback,
                TextBox("item1", {"ja": "テキストボックス", "en": "textbox"}, "デフォルト"),
                RadioButton("item2", {"ja": "ラジオボタン", "en": "radio button"},
                            dict(radio1=True, radio2=False)),
                permissions=["administrator"]
            )
        }
    )
    async def _setting_api_test(self, ctx):
        pass
```

詳細は`rtutil/setting_manager.py`の`SettingManager.setting`のドキュメンテーション見ようね。  
というか大体のバックエンド開発はtasurenってやつがやるから詳細は書かない。