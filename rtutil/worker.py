# RT - Worker

from importlib import import_module
from traceback import format_exc
from websockets import connect
from ujson import loads, dumps
import logging
import asyncio

from .converter import add_converter


class Worker():
    def __init__(self, prefixes, loop=None, logging_level=logging.DEBUG):
        self.queue = asyncio.Queue()
        self.loop = loop if loop else asyncio.get_event_loop()
        self.events = {}
        self.commands = {}
        self.extensions = {}
        self.cogs = {}
        self.ws = None

        # プリフィックスを設定する。
        if isinstance(prefixes, list):
            self.prefixes = tuple(prefixes)
        elif isinstance(prefixes, tuple):
            self.prefixes = prefixes
        elif isinstance(prefixes, str):
            self.prefixes = (prefixes,)
        else:
            raise TypeError("プリフィックスはタプルかリストか文字列にする必要があります。")

        # ログ出力の設定をする。
        logging.basicConfig(
            level=logging_level,
            format="[%(name)s][%(levelname)s] %(message)s"
        )
        self.logger = logging.getLogger("RT - Worker")

        # コマンドフレームワークのコマンドを走らせるためにon_messageイベントを登録しておく。
        self.add_event(self.on_message, "message_create")

        super().__init__()

    def run(self):
        self.loop.run_until_complete(self.worker())

    async def close(self):
        await self.ws.close()

    async def worker(self):
        self.logger.info("Connecting to websocket...")
        # 親のDiscordからのイベントを受け取るmain.pyと通信をする。
        # イベントを受け取ったらそのイベントでの通信を開始する。
        ws = await connect("ws://localhost:3000")
        self.ws = ws
        self.logger.info("Start worker.")
        try:
            while True:
                self.logger.info("Waiting data...")

                # イベントがくるまで待機する。
                data = loads(await ws.recv())
                data = data["data"]

                # イベントでの通信を開始する。
                self.logger.info("Start event communication.")
                while True:
                    callback_data = {
                        "type": "end",
                        "data": {}
                    }

                    # 処理をする。
                    try:
                        # イベントが登録されてるならそれを実行する。
                        if data["type"] in self.events:
                            new_data = data["data"]
                            new_data["callback_template"] = callback_data
                            for coro in self.events[data["type"]]:
                                await coro(ws, new_data)
                    except Exception:
                        error = format_exc()
                    else:
                        error = False

                    callback_data = {
                        "type": "end",
                        "data": {}
                    }

                    # もしエラーが発生しているならエラー落ちしたと伝える。
                    if error:
                        callback_data["type"] = "error"
                        callback_data["data"]["content"] = (error
                                                            if error
                                                            else "エラー不明")

                    # Discordと通信をしてもらったりするためコールバックを送信する。
                    # または通信終了のコールバックを送る。
                    await ws.send(dumps(callback_data))

                    # コールバックを受け取る。
                    data = loads(await ws.recv())
                    if data["type"] == "end":
                        break
                self.logger.info("End event communication.")
        except KeyboardInterrupt:
            pass
        finally:
            await self.close()

    def event(self, event_name=None):
        # イベント登録用のデコレ―タ。
        def _event(coro):
            self.add_event(coro, event_name)
        return _event

    def add_event(self, coro, event_name=None):
        # イベント登録用の関数。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("登録するイベントはコルーチンである必要があります。")
        event_name = event_name if event_name else coro.__name__
        if event_name not in self.events:
            self.events[event_name] = []
        self.events[event_name].append(coro)
        self.logger.info(f"Added event {event_name}.")

    def remove_event(self, coro, event_name=None):
        # イベント削除用の関数。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("登録するイベントはコルーチンである必要があります。")
        event_name = event_name if event_name else coro.__name__
        if event_name in self.events:
            i = -1
            for check_coro in self.events[event_name]:
                i += 1
                if check_coro == coro:
                    del self.events[event_name][i]
                    self.logger.info(f"Removed event {event_name}.")
                    return
        raise ValueError("そのコルーチンはイベントとして登録されていません。")

    def command(self, command_name=None):
        # コマンド登録用のデコレ―タ。
        def _command(coro):
            # converter.pyにあるやつでコンバーターをコマンドのコルーチンに追加する。
            self.add_command(coro, command_name)
        return _command

    def add_command(self, coro, command_name=None):
        # コマンド登録用の関数。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("登録するコマンドはコルーチンである必要があります。")
        command_name = command_name if command_name else coro.__name__
        self.commands[command_name] = coro
        self.logger.info(f"Added command {command_name}")

    def remove_command(self, coro, command_name=None):
        # コマンド削除用の関数。
        command_name = command_name if command_name else coro.__name__
        if (not asyncio.iscoroutinefunction(coro)
                or command_name not in self.commands):
            raise TypeError("削除するコマンドはコルーチンである必要があります。")
        del self.commands[command_name]
        self.logger.info(f"Added command {command_name}")

    async def process_commands(self, ws, data):
        # コマンドを走らせる。
        if data["content"].startswith(self.prefixes):
            for command_name in self.commands:
                for prefix in self.prefixes:
                    start = prefix + command_name
                    if data["content"].startswith(start):
                        # コマンドの準備をする。
                        # 引数を取り出してからコンバーターをコマンドのプログラムにつけて実行する。
                        args = self.parse_args(
                            data["content"].replace(start, ""))
                        cmd = add_converter(
                            self.commands[command_name], ws, data, None, *args)
                        asyncio.create_task(cmd)
                        return command_name

    async def on_message(self, ws, data):
        await self.process_commands(ws, data)

    def parse_args(self, content: str) -> list:
        # 引数を取り出す。
        args, raw_arg = [], ""
        now_split_char = False
        for c in content:
            if c in (" ", "　", "\t", "\n") and not now_split_char:
                if raw_arg:
                    args.append(raw_arg)
                    raw_arg = ""
            elif c in ("'", '"'):
                now_split_char = False if now_split_char else True
            else:
                raw_arg += c
        if raw_arg:
            args.append(raw_arg)
        return args

    def get_filename(self):
        return __name__

    def add_cog(self, cog_class):
        setattr(cog_class, "get_filename", self.get_filename)
        self.cogs[cog_class.__name__] = {
            "__name__": cog_class.get_filename(),
            "cog": cog_class
        }

    def remove_cog(self, name):
        del self.cogs[name]

    def load_extension(self, path):
        self.extensions[path] = import_module(path)
        return self.extensions[path].setup(self.bot)

    def unload_extension(self, path):
        for key in self.cogs:
            if self.cogs[key]["__name__"] == path:
                del self.cogs[key]
        del self.extensions[path]


if __name__ == "__main__":
    worker = Worker()
    worker.run()
