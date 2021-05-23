# RT - Worker

from websockets import connect
from ujson import loads, dumps
from traceback import format_exc
import logging
import asyncio


class Worker():
    def __init__(self, loop=None, logging_level=logging.DEBUG):
        self.queue = asyncio.Queue()
        self.loop = loop if loop else asyncio.get_event_loop()

        # ログ出力の設定をする。
        logging.basicConfig(
            level=logging_level,
            format="[%(name)s][%(levelname)s] %(message)s"
        )
        self.logger = logging.getLogger("RT - Worker")

    def run(self):
        self.loop.run_until_complete(self.worker())

    async def worker(self):
        self.logger.info("Connecting to websocket...")
        async with connect("ws://localhost:3000") as ws:
            self.logger.info("Start worker.")
            while True:
                self.logger.info("Waiting data...")

                # イベントがくるまで待機する。
                data = loads(await ws.recv())
                data = data["data"]
                self.logger.info("Received data!")

                # イベントでの通信を開始する。
                self.logger.info("Start event communication.")
                while True:
                    callback_data = {
                        "type": "end",
                        "data": {}
                    }

                    # 処理をする。
                    try:
                        if data["type"] == "on_message":
                            if data["content"] == "r2!test":
                                callback_data["type"] = "discord"
                                callback_data["data"]["type"] = "send"
                                callback_data["data"]["args"] = ["From worker"]
                                await ws.send(dumps(callback_data))
                                data = loads(await ws.recv())
                                print(data["data"]["message_id"])
                    except Exception:
                        error = format_exc()
                    else:
                        error = False

                    callback_data = {
                        "type": "end",
                        "data": {}
                    }

                    # もしエラーが発生しているならエラー落ち下と伝える。
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


if __name__ == "__main__":
    worker = Worker()
    worker.run()
