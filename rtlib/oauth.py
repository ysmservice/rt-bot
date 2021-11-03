# rtlib - OAuth

from typing import Union, Optional, List, Tuple, Callable
from discord.ext import tasks
from random import randint
from time import time
import discord
import aiohttp
import reprypt
import sanic
import ujson


def require_session(coro: Callable) -> Callable:
    # aiohttp.ClientSessionが作られてなければ作るデコレータ。
    async def new(self, *args, **kwargs):
        if self.cs is None:
            self.cs = aiohttp.ClientSession(
                json_serialize=ujson.dumps, raise_for_status=True,
                loop=self.bot.loop
            )
        return await coro(self, *args, **kwargs)
    return new


class OAuth:
    """DiscordOAuth認証ログインシステムを簡単に作るためのものです。

    Notes
    -----
    これはコグの中でしか使えないのでご注意ください。
    
    Parameters
    ----------
    bot
        Discordのbotクライアントです。  
        `bot.web`に`sanic.Sanic`がある必要があります。
    client_id : str
        OAuthのクライアントIDです。
    client_secret : str
        OAuthのクライアントシークレットです。
    secret_key : str, default str(time.time() / random.randint(2, 100)) * 2
        セッションを暗号化して保存する時の暗号化に使うキーです。  
        デフォルトではランダムで毎回起動時に生成されます。"""

    BASE = "https://discord.com/api/v8/"

    def __init__(
            self, bot, client_id: str, client_secret: str,
            secret_key: str = str(time() / randint(2, 100)) * 2
    ):
        self.app, self.bot, self.cs = bot.web, bot, None

        self.client_id, self.client_secret = client_id, client_secret
        self.secret_key = secret_key

        self.bot.web_manager.events["on_route_add"].append(self._on_route_add)
        self.runnings = {}

    @tasks.loop(seconds=30)
    async def remove_runnings_queue(self):
        now = time()
        for ip in list(self.runnings.keys()):
            if now - self.runnings[ip] > 180:
                del self.runnings[ip]

    @require_session
    async def get_url(
            self, redirect_url: str,
            scope: Union[List[str], Tuple[str, ...]]) -> str:
        """OAuthログイン用のURLを取得します。  
        `rtlib.OAuth`にて使われます。
        
        Parameters
        ----------
        redirect_url : str
            認証後リダイレクトするURL。
        scope : Union[List[str], Tuple[str, ...]]
            OAuthのscopeです。"""
        params = {
            "response_type": "code",
            "scope": "%20".join(scope),
            "client_id": self.client_id,
            "redirect_uri": redirect_url
        }
        async with self.cs.get(self.BASE + "oauth2/authorize", params=params) as r:
            url = str(r.url)
        return url[:(slash := url.find("?"))] + url[slash:].replace("/", r"%2F")

    @require_session
    async def _get_token(
            self, code: str, callback_url,
            scope: Union[List[str], Tuple[str, ...]]) -> dict:
        # OAuthから渡されたcodeから一時TOKENを取得する関数です。
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": callback_url
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        try:
            async with self.cs.post(
                    self.BASE + "oauth2/token", data=data, headers=headers) as r:
                data: dict = await r.json(loads=ujson.loads)
        except aiohttp.client_exceptions.ClientResponseError as e:
            raise ValueError("ごめんなさい！Discordから渡されたコードから情報を取得できなかったのですぅ...\n"
                             + f"申し訳ないんですがもう一度再挑戦してほしいんです！:{e}")
        return data

    @require_session
    async def _get_userdata(self, token: str) -> dict:
        # TOKENからユーザーデータを取得する関数です。
        async with self.cs.get(
                self.BASE + "users/@me", headers={
                    "Authorization": f"Bearer {token}"}) as r:
            data = await r.json(loads=ujson.loads)
        return data

    def get_user_from_cookies(self, cookie_data: str) -> Optional[discord.User]:
        try:
            userdata = ujson.loads(
                reprypt.decrypt(cookie_data, self.secret_key)
            )
        except reprypt.DecryptError:
            return None
        else:
            return self.bot.get_user(int(userdata["user_id"]))

    async def _callback(
            self, code: str, callback_url: str,
            callback_uri: str, scope: Union[List[str], Tuple[str, ...]]):
        # OAuth認証後にリダイレクトされるrouteです。
        # OAuth認証からもらったcodeで一時TOKENを取得する。
        data = await self._get_token(code, callback_url, scope)
        token = data["access_token"]

        # userdataからidと名前を取り出してクッキーに入れるものを作る。
        data = await self._get_userdata(token)
        cookie_data = {"user_id": data["id"], "name": data["username"]}

        # クッキーに暗号化してから入れる。
        print(callback_url, callback_uri)
        response = sanic.response.redirect(callback_uri)
        response.cookies["session"] = reprypt.encrypt(
            ujson.dumps(cookie_data), self.secret_key
        )

        return response

    def _make_new_route(
            self, coro, require: bool, want: bool,
            scope: Union[List[str], Tuple[str, ...]] = ("identify",)):
        # routeをログインシステムで使えるようにラップするための関数。
        async def new(*args, **kwargs):
            request = [arg for arg in args
                        if isinstance(arg, sanic.request.Request)][0]
            request_index = args.index(request)
            request = args[request_index]
            if request.ip in self.runnings:
                raise sanic.exceptions.SanicException(
                    "同時にログインをしようとすることはできません。\nもし同時じゃない場合は二分後にもう一度アクセスしてください。"
                )
            else:
                self.runings[request.ip] = time()

            if ((not (userdata := request.cookies.get("session"))
                     and (code := request.args.get("code"))) and require):
                # もしまだログインが終わってないなら。
                # もし認証後ならcodeをtokenにしてクッキーに情報を保存する。
                # その後またこのrouteにリダイレクトする。
                try:
                    response = await self._callback(
                        code, request.url[:request.url.find("?")],
                        request.path, scope
                    )
                except Exception as e:
                    if request.ip in self.runnings:
                        del self.runings[request.ip]
                    raise sanic.exceptions.SanicException(
                        f"OAuth認証に失敗しました。\n> {e}", status_code=500
                    )
                else:
                    return response
                user = None
            elif userdata:
                # もしログイン済みならクッキーに記録されてるユーザーデータを複合化して取得する。
                user = self.get_user_from_cookies(userdata)
            else:
                user = None

            if user is None and not want:
                # もしユーザーの取得に失敗したまたはOAuth認証をしていないならOAuth認証をさせる。
                # しかしlogin_wantの場合はここをスキップする。
                if userdata:
                    if userdata[0] == "{":
                        # もしユーザーデータを取得することができているのにユーザーオブジェクトを取得していないなら例外を発生させる。
                        # こうしないとintentsのメンバーが有効じゃない時などにずっと認証画面という無限ループが発生してしまう。
                        # 無限ループって怖くね？
                        raise sanic.exceptions.SanicException(
                            "OAuth認証に失敗しました。\n> ユーザーデータの取得に失敗しました。"
                            + "すみません、RTを使ってる人ですか...？(メイド風の喋り方で。)")
                return sanic.response.redirect(
                    await self.get_url(request.url, scope)
                )

            if request.ip in self.runnings:
                del self.runings[request.ip]
            # routeに渡すrequestにユーザーオブジェクトを付け加える。
            args[request_index].ctx.user = user
            # デコレータが付いているコルーチン関数を実行する。
            return await coro(*args, **kwargs)
        new.__name__ = coro.__name__
        return new

    async def _on_route_add(self, route):
        # Routeが`commands.Cog.route`によって追加された際に呼び出されます。
        require = getattr(route, "_login_require", False)
        want = getattr(route, "_login_want", False)

        if require or want:
            # ログインシステムが使えるようにするためにラップする。
            route = self._make_new_route(
                route, require, want, **(require[1] if require else want[1]))

        return route

    @staticmethod
    def login_require(**kwargs):
        """ログインが必要なrouteに付けるデコレータです。  
        このデコレータをつけるとrouteにアクセスされた際に、ログインしていないならログインをしてから再度routeにアクセスされます。  
        そして`request.user`にログインしているdiscord.pyのユーザーオブジェクトが入ります。"""
        def decorator(coro):
            coro._login_require = (1, kwargs)
            return coro
        return decorator

    @staticmethod
    def login_want(**kwargs):
        """ログインしてるといいなというrouteにつけるデコレータです。  
        このデコレータをつけるとログイン済みの場合のみrouteに渡される`request`の`request.user`が有効になります。になります。  
        ログインしていない場合は`request.user`がNoneとなります。"""
        def decorator(coro):
            coro._login_want = (1, kwargs)
            return coro
        return decorator

    def __del__(self):
        if self.cs:
            self.cs.close()
