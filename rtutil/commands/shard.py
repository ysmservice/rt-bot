# RT - Shard

import discord

from multiprocessing import Pool, Queue
import asyncio


class Worker():
    def listening_event(self, queue):
        print(1)
        while True:
            current_queue = queue.get(True)
            # キューが回ってきたらイベントを処理する。
            print(current_queue)
            if current_queue:
                event_type, data = current_queue
                if event_type == "stop_worker":
                    break
                if event_type == "on_message":
                    print(data["content"])


class RTShardClient(discord.AutoShardedClient):
    def __init__(self, default_worker_count: int,
                  max_worker: int,  *args, **kwargs):
        # ログ出力を準備する。
        self._print = ((lambda title, text: print("[" + title + "]", text))
                        if kwargs.get("log", False)
                        else lambda title, text: (title, text))
        # workerを動かす。
        self._print("RT - Process Pool", "Process Pool is setting now!")
        self.pool = Pool(max_worker)
        self.queue = Queue()
        for i in range(default_worker_count):
            self._print(
                "RT - Process Pool",
                f"Process Pool is setting worker {i}."
            )
            target_worker = Worker()
            self.pool.apply_async(target_worker.listening_event,
                                     args=(self.queue,))
        self._print("RT - Process Pool", "Process Pool setting done!")

        super().__init__(*args, **kwargs)

    async def on_message(self, message):
        data = {
            "guild.name": message.guild.name,
            "channel.name": message.channel.name,
            "author": message.author.name,
            "content": message.content,
            "clean_content": message.clean_content
        }

        self.queue.put(["on_message", data])

    def __del__(self):
        self.pool.close()
