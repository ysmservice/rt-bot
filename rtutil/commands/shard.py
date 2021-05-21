# RT - Shard

import discord

from .events import *

from multiprocessing import Pool, Manager
from threading import Thread
from queue import Empty
from os import cpu_count
import asyncio


class Worker():
    def listening_event(self, queue, callback):
        self.callback = callback
        while True:
            current_queue = queue.get(True)
            # キューが回ってきたらイベントを処理する。
            if current_queue:
                event_type, data = current_queue
                if event_type == "closed":
                    # Botがcloseしたならループを抜ける。
                    break
                if event_type == "on_message":
                    if data["message"]["content"] == "r2!close":
                        callback.put(["close_client", None])
                        break
        # Worker終了済み通知をする。
        callback.put(["worker_closed", None])

    def send(self, channel_id: int, *args, **kwargs):
        data = {
            "channel_id": channel_id,
            "args": args,
            "kwargs": kwargs
        }
        self.callback.put(["send", data])


class RTShardClient(discord.AutoShardedClient):
    def __init__(self, *args, **kwargs):
        # ログ出力を準備する。
        self._print = ((lambda title, text: print("[" + title + "]", text))
                        if kwargs.get("log", False)
                        else lambda title, text: (title, text))
        self.TITLE = "RT - Process Pool"
        self._print("RT - Client", "Now setting...")
        self._print("RT - Client", "You can print some log by client._print().")

        self.events = {}
        super().__init__(*args, **kwargs)

        # Worker作成の偈準備をする。
        self._print(self.TITLE, "Process worker setting now!")
        self.max_worker = kwargs.get("max_worker", cpu_count())
        self.default_worker_count = kwargs.get("default_worker_count", 5)
        self.pool = Pool(self.max_worker)
        self.manager = Manager()
        # イベント通知用のQueueを作成する。
        self.queue = self.manager.Queue()
        # イベント処理中にDiscordになにかしてほしいときに通知する用のQueueを作成する。
        self.callback = self.manager.Queue()

        self.closed_worker = 0

        # Workerを動かす。
        for i in range(self.default_worker_count):
            self._print(
                self.TITLE, f"Setting worker {i}...")
            target_worker = Worker()
            self.pool.apply_async(
                target_worker.listening_event,
                (self, self.queue, self.callback), error_callback=self.on_error_worker
            )
        self._print(self.TITLE, "Done!")

        # callback_workerを実行する。
        self.loop = asyncio.get_event_loop()
        self._print("RT - Callback Threads", "Setting now!")
        self.max_callback_worker = kwargs.get("max_callback_worker", 3)
        self.closed_callback_worker = 0
        self.threads = []
        for i in range(self.max_callback_worker):
            self._print("RT - Callback Threads",
                         f"Setting callback_worker {i}...")
            thread = Thread(target=self.run_callback, args=(self.callback,),
                              name=f"RT-callback-worker-{i}")
            thread.start()
            self.threads.append(thread)
        self._print("RT - Callback Threads", "Done!")

        add_event_hook(self, self.queue)

    def run_callback(self, callback):
        while True:
            # Callbackを処理する。
            try:
                current_queue = callback.get_nowait()
            except Empty:
                current_queue = None
            except ValueError:
                pass
            if current_queue:
                event_type, data = current_queue
                # Workerが閉じたよって言ったならカウントしておく。
                if event_type == "worker_closed":
                    self.closed_worker += 1
                    self._print(
                        self.TITLE,
                        f"Closed worker {self.closed_worker - 1}..."
                    )
                # close_clientならClientをcloseする。
                if event_type == "close_client":
                    self._print("RT - Client", "Closing client...")
                    self.loop.create_task(self.close())
            # もしClientが閉じられているならWorkerをストップする。
            if self.is_closed():
                # もしWorkerが全員終了したならこのCallback Workerをストップする。
                # もしWorkerがまだ全員終了していないなら終了通知をする。
                if self.closed_worker == self.default_worker_count:
                    break
                else:
                    self.queue.put(["closed", None])
        self.closed_callback_worker += 1
        if self.closed_callback_worker == self.max_callback_worker:
            self.pool.close()
            self._print("RT - Client", "Closed!")

    def on_error_worker(self, e):
        self._print(self.TITLE, "Error on worker! : " + str(e))
        coros = self.events.get("on_error_worker")

    def add_event(self, coro):
        # イベントの登録デコレータ。
        # もしコルーチンじゃなかったらTypeErrorを発生させる。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("登録するイベントはコルーチンにする必要があります。")
        # イベントを登録する。
        if coro.__name__ in self.events:
            self.events[coro.__name__].append(coro)
        else:
            self.events[coro.__name__] = [coro]
        self._print("RT - Event Manager", "Event registered.")

        return coro

    def remove_event(self, coro):
        # イベントの登録解除デコレータ。
        # もしコルーチンじゃなかったらTypeErrorを発生させる。
        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("登録するイベントはコルーチンにする必要があります。")
        # イベントの登録を解除する。
        if coro.__name__ in self.events:
            del self.events[coro.__name__]
        else:
            raise TypeError("そのイベントはまだ登録されていません。")

    def __del__(self):
        if not self.is_closed():
            self.close()
