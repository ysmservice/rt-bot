# RT - Shard

import discord

import threading
import asyncio


class Worker(discord.Client):
    def __init__(self, bot):
        self.bot = bot
        self.queues = []
        self.login(bot.data["token"])
        self.Super.__init__(loop=asyncio.new_event_loop())

    async def listening_event(self):
        while True:
            for event_type, data in self.queues:
                if event_type == "stop_worker":
                    break
                if event_type == "on_message":
                    print(data["content"])

        self.close()


class RTShardClient(discord.AutoShardedClient):
    def __init__(self, default_worker_count: int, *args, **kwargs):
        self.workers = []

        # workerを動かす。
        for _ in range(default_worker_count):
            self.add_worker()

        self.Super().__init__(*args, **kwargs)

    # workerを停止させる。
    def remove_worker(self, index: int):
        self.add_queue("stop_worker", {}, index)
        del self.workers[index]

    # workerを追加する。
    def add_worker(self):
        worker = Worker(self.bot)
        thread = threading.Thread(
            target=worker.login,
            name=f"RT-Worker-{len(self.workers)}",
            args=(self.bot.data["token"],)
        )
        thread.start()
        self.workers.append(worker)

    # queueを追加する。
    def add_queue(self, event_type: str, data: dict, worker_index: int = None):
        worker = self.workers[0]["worker"]
        queue_length = len(self.workers[0]["queue"])

        # workerの指定がないなら一番queueが少ないのを探してそこにqueueを追加する。。
        if worker_index is None:
            for worker in self.workers[1:]:
                if len(worker["queue"]) < queue_length:
                    queue_length = worker["queue"]
                    worker = worker["worker"]
        else:
            worker = self.workers[worker_index]

        # workerにqueueを追加する。
        worker.queues.append([event_type, data])

    async def on_message(self, message):
        data = {
            "message": message,
            "guild": message.guild,
            "channel": message.channel,
            "author": message.author,
            "content": message.content,
            "clean_content": message.clean_content
        }

        self.add_queue("on_message", data)
