# RT - Shard

import discord

from .type_manager import TypeManager

from multiprocessing import Pool, Manager
import asyncio


class Worker():
    def listening_event(self, queue):
        loop = asyncio.new_event_loop()
        while True:
            current_queue = queue.get(True)
            # キューが回ってきたらイベントを処理する。
            if current_queue:
                event_type, data = current_queue
                if event_type == "stop_worker":
                    break
                if event_type == "on_message":
                    pass

    async def send(self, channel_id: int, *args, **kwargs):
        pass


class RTShardClient(discord.AutoShardedClient, TypeManager):
    def __init__(self, *args, **kwargs):
        # ログ出力を準備する。
        self._print = ((lambda title, text: print("[" + title + "]", text))
                        if kwargs.get("log", False)
                        else lambda title, text: (title, text))
        self.TITLE = "RT - Process Pool"

        # workerを動かす。
        self._print(self.TITLE, "Setting now!")
        self.pool = Pool(kwargs.get("max_worker"))
        self.manager = Manager()
        self.queue = self.manager.Queue()

        for i in range(kwargs.get("default_worker_count", 5)):
            self._print(
                self.TITLE, f"Setting worker {i}...")
            target_worker = Worker()
            self.pool.apply_async(
                target_worker.listening_event,
                (self.queue,), error_callback=self.on_error_worker
            )
        self._print(self.TITLE, "Done!")

        super().__init__(*args, **kwargs)

    def on_error_worker(self, e):
        self._print(self.TITLE, "Error on worker! : " + str(e))

    async def on_message(self, message):
        self.queue.put(["on_message", self.message_to_dict(message)])

    def __del__(self):
        self.pool.close()
