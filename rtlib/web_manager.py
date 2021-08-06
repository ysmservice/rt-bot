# rtlib - Web Manager

from sanic import Sanic, exceptions, response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from flask_misaka import Misaka

from typing import Union, List, Tuple
from discord.ext import commands
from traceback import print_exc
from inspect import getmembers
from os.path import exists


class WebManager:
    """ウェブサーバーを簡単に管理するためのクラスです。  
    `rtlib.Backend`で使用されます。  
    もしこれを`rtlib.Backend`じゃなく普通のdiscord.pyの`commands.Bot`などで使いたい場合は、`bot.web = sanic.Sanic()`のようにしてそれを引数のbotに渡しましょう。  
    もし`rtlib.Backend`を使用する人でこのクラスに何かしらキーワード引数を渡したい場合は、`rtlib.Backend`のキーワード引数である`web_manager_kwargs`を使用してください。  
    これを有効にすると`discord.ext.commands.Cog.route`が使えるようになり、エクステンションでrouteを登録してリロードもできるようになります。

    Notes
    -----
    これは`bot.load_extension("rtlib.libs.on_cog_add")`が自動で実行されます。

    Parameters
    ----------
    bot : Backend
        `rtlib.Backend`のインスタンスです。
    folder : str, default "templates"
        ファイルアクセスがあった際にどのフォルダにあるファイルを返すかです。  
        デフォルトの`templates`の場合は`wtf.html`にアクセスされた際に`templates/wtf.html`のファイルを返します。
    template_engine_exts : Union[List[str], Tuple[str]], default ("html", "xml", "tpl")
        Jinja2テンプレートエンジンを使用して返すファイルのリストです。""" # noqa
    def __init__(self, bot, folder: str = "templates",
                 template_engine_exts: Union[List[str], Tuple[str]] = ("html", "xml", "tpl")):
        self.template_engine_exts = template_engine_exts
        self.bot, self.web, self.folder = bot, bot.web, folder

        # Jinja2テンプレートエンジンを定義する。
        self._env = Environment(
            loader=FileSystemLoader(folder),
            autoescape=select_autoescape(template_engine_exts),
            enable_async=True
        )
        # Jinja2テンプレートエンジンにmarkdownのフィルターを追加する。
        self._env.filters.setdefault(
            "markdown", Misaka(autolink=True, wrap=True).render)

        # SanicにRouteなどを追加する。
        self.web.register_middleware(self._on_response, "response")

        # on_readyをセットアップする。する。
        if not hasattr(bot, "_rtlib"):
            self._setup()

    def _setup(self):
        # commands.Cog.routeからrouteを登録できるようにする。
        self._routes = {}
        self._added_routes = []
        self.events = {"on_route_add": [], "on_route_remove": []}
        self.bot.load_extension("rtlib.ext.on_cog_add")
        self.bot.add_listener(self._on_cog_add, "on_cog_add")
        self.bot.add_listener(self._on_cog_remove, "on_cog_remove")

        # commands.Cog.routeを作る。
        commands.Cog.route = self._route

    def _route(self, *args, **kwargs):
        # commands.Cog.routeのためのもの。
        def decorator(coro):
            coro._route = (coro, args, kwargs)
            return coro
        return decorator

    async def _wrap_error_log(self, coro, name, default=None):
        # 渡されたコルーチンをエラーハンドリングして実行する。
        try:
            return await coro
        except Exception:
            print(f"Exception on `{name}`:")
            print_exc()
            return default

    async def _on_cog_add(self, cog):
        # コグがロードされた際に呼び出されます。commands.Cog.routeのためのもの。
        routes = [coro._route for _, coro in getmembers(cog)
                  if hasattr(coro, "_route")]

        for coro, args, kwargs in routes:
            # routeリストに`commands.Cog.route`がくっついてるやつを登録する。
            name = cog.__class__.__name__

            # カスタムイベントを走らせる。
            route_full_name = f"{name}.{coro.__name__}"
            for event in self.events["on_route_add"]:
                coro = await self._wrap_error_log(event(coro), route_full_name, coro)

            # routeリストに登録をする。
            if name not in self._routes:
                self._routes[name] = {}
            self._routes[name][coro.__name__] = coro

            if route_full_name not in self._added_routes:
                # もしsanicにrouteをまだ登録していないなら登録をする。
                # self._added_routesはcommands.Cog.routeが付いているrouteの関数を実行するrouteが、sanicにもう追加したかどうかを調べるためのもの。

                async def main_route(*args, cog_name=name, coro_name=coro.__name__, **kwargs):
                    async def main_route():
                        # 登録するrouteの関数(commands.Cog.routeが付いてるやつ)があれば実行する。
                        route = self._routes[cog_name][coro_name]
                        if route_full_name in self._added_routes:
                            return await route(cog, *args, **kwargs)
                        else:
                            raise exceptions.SanicException("Requested URL not found", status_code=404)
                    return await main_route()

                self.web.add_route(main_route, *args, **kwargs)
                self._added_routes.append(route_full_name)
            del coro

    async def _on_cog_remove(self, cog):
        # コグが削除された際に呼ばれます。commands.Cog.routeのためのもの。
        # routeの中で実行するrouteの関数(coommands.Cog.routeが付いてるやつ)を削除する。
        routes = self._routes.get((name := cog.__class__.__name__), {})
        delete = []
        for key in routes:
            for event in self.events["on_route_remove"]:
                await self._wrap_error_Log(
                    event(self._routes[name][key]),
                    f"Exception on route '{name}.{key}':",
                    self._routes[name][key]
                )
            delete.append(key)
        for key in delete:
            del self._routes[name][key]
        del delete

    async def _on_response(self, request, res):
        # Sanicがレスポンスを返す時に呼ばれる関数です。
        # もしRouteが見つからなかったならファイルを返すことを試みる。
        if ((b"Requested" in res.body or b"not found" in res.body)
                and res.status == 404):
            path = request.path[1:]
            true_path = self.folder + "/" + path
            # もしフォルダでindex.htmlが存在するならpathをそれに置き換える。
            end_slash = true_path[-1] == "/"
            if_index = (true_path[:-1] if end_slash else true_path) + "/index.html"
            if exists(if_index):
                path = if_index[if_index.find("/"):]
                true_path = if_index
            # ファイルが存在しないなら404を返す。存在するならファイルを返す。
            if exists(true_path):
                # もしテンプレートエンジンを使い返すファイルならそれでファイルを返す。
                if path.endswith(self.template_engine_exts):
                    return await self.template(path)
                else:
                    return await response.file(true_path)
            else:
                return exceptions.abort(
                    f"{path}が見つからなかった...\nアクセスしたお客様〜、ごめんちゃい！(スターフォックス64のあれ風)",
                    status_code=404
                )

    async def template(self, path: str, **kwargs) -> response.HTTPResponse:
        """Jinja2テンプレートエンジンを使用してファイルを返します。  
        pathに渡されたファイルはこのクラスの定義時に渡した引数であるfolderのフォルダーにある必要があります。  
        `rtlib.Backend`を使っている場合は`rtlib.Backend`の定義時にキーワード引数の`web_manager_kwargs`からfolderの引数を設定したりしてください。

        Parameters
        ----------
        path : str
            テンプレートエンジンを使用して返すファイルのパスです。
        **kwargs
            テンプレートエンジンに渡す引数です。

        Returns
        -------
        response : sanic.response.HTTPResponse
            HTMLのレスポンスです。

        Examples
        --------
        @bot.web.route("/who_are_you")
        async def whoareyou(request):
            return bot.web_manager.template("im_god.html")""" # noqa
        return response.html(await self._env.get_template(path).render_async(kwargs))
