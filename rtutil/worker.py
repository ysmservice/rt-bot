# RT - Worker

from websockets import connect
from ujson import loads, dumps
from traceback import format_exc
import logging
import asyncio
import discord


class Worker(discord.Client):
    def __init__(self, loop=None, logging_level=logging.DEBUG):
        self.queue = asyncio.Queue()
        self.loop = loop if loop else asyncio.get_event_loop()
        self.events = {}

        # ログ出力の設定をする。
        logging.basicConfig(
            level=logging_level,
            format="[%(name)s][%(levelname)s] %(message)s"
        )
        self.logger = logging.getLogger("RT - Worker")

        super().__init__()

    def run(self):
        self.loop.run_until_complete(self.worker())

    async def worker(self):
        self.logger.info("Connecting to websocket...")
        # 親のDiscordからのイベントを受け取るmain.pyと通信をする。
        # イベントを受け取ったらそのイベントでの通信を開始する。
        async with connect("ws://localhost:3000") as ws:
            self.logger.info("Start worker.")
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
                        print(data)
                        # イベントが登録されてるならそれを実行する。
                        if data["type"] in self.events and 1 == 2:
                            data["callback_template"] = callback_data
                            self.logger.debug(self.events)
                            for coro in self.events[data["type"]]:
                                await coro(ws, data)
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

    def event(self, coro, event_name=None):
        # イベント登録用のデコレ―タ。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("登録するイベントはコルーチンである必要があります。")
        event_name = event_name if event_name else coro.__name__
        if event_name not in self.events:
            self.events[event_name] = []
        self.events[event_name].append(coro)
        self.logger.info(f"Added event {event_name}.")

    def remove_event(self, coro, event_name=None):
        # イベント削除用。
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


if __name__ == "__main__":
    worker = Worker()
    worker.run()
