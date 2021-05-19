# RT - Shard

import discord

from .type_manager import TypeManager

from threading import Thread
from multiprocessing import Pool, Manager
import asyncio


class Worker():
    def listening_event(self, queue, callback):
        self.callback = callback
        while True:
            current_queue = queue.get(True)
            # キューが回ってきたらイベントを処理する。
            if current_queue:
                event_type, data = current_queue
                if event_type == "on_message":
                    print(1)
                    self.send(data["message"]["channel"]["id"], "test")

    def send(self, channel_id: int, *args, **kwargs):
        data = {
            "channel_id": channel_id,
            "args": args,
            "kwargs": kwargs
        }
        self.callback.put(["send", data])


class RTShardClient(discord.AutoShardedClient, TypeManager):
    def __init__(self, *args, **kwargs):
        # ログ出力を準備する。
        self._print = ((lambda title, text: print("[" + title + "]", text))
                        if kwargs.get("log", False)
                        else lambda title, text: (title, text))
        self.TITLE = "RT - Process Pool"

        # workerを動かす。
        self._print(self.TITLE, "Setting now!")
        max_worker = kwargs.get("max_worker")
        self.pool = Pool(max_worker)
        self.manager = Manager()
        self.queue = self.manager.Queue()
        self.callback = self.manager.Queue()

        for i in range(kwargs.get("default_worker_count", 5)):
            self._print(
                self.TITLE, f"Setting worker {i}...")
            target_worker = Worker()
            self.pool.apply_async(
                target_worker.listening_event,
                (self.queue, self.callback), error_callback=self.on_error_worker
            )
        self._print(self.TITLE, "Done!")

        # callback_workerを実行する。
        self.loop = asyncio.get_event_loop()
        self._print("RT - Callback Threads", "Setting now!")
        self.threads = []
        for i in range(kwargs.get("max_callback_worker", 3)):
            self._print("RT - Callback Threads",
                         f"Setting callback_worker {i}...")
            thread = Thread(target=self.run_callback, args=(self.callback,),
                              name=f"RT-callback-worker-{i}")
            thread.start()
            self.threads.append(thread)
        self._print("RT - Callback Threads", "Done!")

        self._print("RT - Client", "Setting now!")
        super().__init__(*args, **kwargs)

    def run_callback(self, callback):
        while True:
            # Callbackを処理する。
            current_queue = callback.get(True)
            if current_queue:
                event_type, data = current_queue
                if event_type == "send":
                    channel = self.get_channel(data["channel_id"])
                    self.loop.create_task(
                        channel.send(*data["args"], **data["kwargs"]))
            # もしClientが閉じられているかつqueueがもうないならループを抜ける。
            if self.is_closed():
                if current_queue:
                    self.queue.put(["closed", None])

    def on_error_worker(self, e):
        self._print(self.TITLE, "Error on worker! : " + str(e))

    async def on_message(self, message):
        self.queue.put(["on_message", self.message_to_dict(message)])

    def __del__(self):
        for thread in self.threads:
            thread.join()
        self.pool.close()
