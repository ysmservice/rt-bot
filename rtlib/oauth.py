# rtlib - OAuth

from typing import Union, List, Tuple, Callable
from aiohttp import ClientSession
from random import randint
from time import time
import discord
import reprypt
import sanic
import ujson


def RequireSession(coro: Callable) -> Callable:
    # aiohttp.ClientSessionが作られてなければ作るデコレータ。
    async def new(self, *args, **kwargs):
        if self.cs is None:
            self.cs = ClientSession(
                json_serialize=ujson.dumps, raise_for_status=True,
                loop=self.bot.loop
            )
        return await coro(self, *args, **kwargs)
    return new


class OAuth:

    BASE = "https://discord.com/api/v8/"

    def __init__(
            app: sanic.Sanic, bot: discord.Client, client_id: str,
            client_secret: str, scope: Union[List[str], Tuple[str, ...]],
            redirect_uri: str = "/", callback_uri: str = "callback",
            callback_url: str = "http://localhost:8000/callback",
            secret_key: str = str(time() / randint(2, 100)),
    ):
        self.app, self.bot, self.cs = app, bot, None

        print(secret_key)
        self.client_id, self.client_secret = client_id, client_secret
        self.callback_url, self.secret_key = callback_url, secret_key,
        self.redirect_uri, self.scope = redirect_uri, "%20".join(scope)

        self.app.add_route(self._callback, "/" + callback_uri)

    @RequireSession
    async def _get_token(self, code: str) -> dict:
        # OAuthから渡されたcodeから一時TOKENを取得する関数です。
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.callback_url,
            "scope": self.scope
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        async with self.cs.get(
                self.BASE + "oauth2/token", data=data, headers=headers) as r:
            data: dict = await r.json(loads=ujson.loads)
        return data

    @RequireSession
    async def _get_userdata(self, token: str) -> dict:
        # TOKENからユーザーデータを取得する関数です。
        async with self.cs.get(
                self.BASE + "users/@me", headers={
                    "Authorization": f"Bearer {token}"}) as r:
            data = await r.json(loads=ujson.loads)
        return data

    async def _callback(self, request):
        # OAuth認証後にリダイレクトされるrouteです。
        # OAuth認証からもらったcodeで一時TOKENを取得する。
        data = await self._get_token(request.args.get("code"))
        token = data["token"]

        # userdataからidと名前を取り出してクッキーに入れるものを作る。
        userdata = await self._get_userdata(token)
        cookie_data = {"user_id": data["id"], "name": data["name"]}

        # クッキーに暗号化してから入れる。
        response = sanic.response.redirect(self.redirect_uri)
        response["session"] = reprypt.encrypt(ujson.dumps(cookie_data), self.secret_key)
        print(resonse["session"])
        return response
