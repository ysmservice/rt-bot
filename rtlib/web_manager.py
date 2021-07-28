# rtlib - Web Manager

from typing import Union, List, Tuple

from sanic import Sanic, exceptions, response

from jinja2 import Environment, FileSystemLoader, select_autoescape
from flask_misaka import Misaka

from os.path import exists


class WebManager:
    """ウェブサーバーを簡単に管理するためのクラスです。  
    `rtlib.Backend`で使用されます。  
    もしこれを`rtlib.Backend`じゃなく普通のdiscord.pyの`commands.Bot`などで使いたい場合は、`bot.web = sanic.Sanic()`のようにしてそれを引数のbotに渡しましょう。  
    もし`rtlib.Backend`を使用する人でこのクラスに何かしらキーワード引数を渡したい場合は、`rtlib.Backend`のキーワード引数である`web_manager_kwargs`を使用してください。

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

    async def _on_response(self, request, res):
        # Sanicがレスポンスを返す時に呼ばれる関数です。
        # もしRouteが見つからなかったならファイルを返すことを試みる。
        if ((b"requested" in res.body or b"not found" in res.body)
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
                    404, message=f"{path}が見つからなかった...\nアクセスしたお客様〜、ごめんちゃい！(スターフォックス64のあれ風)") # noqa

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
