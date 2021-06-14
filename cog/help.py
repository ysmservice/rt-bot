# RT - Help

import rtutil


class Help(metaclass=rtutil.Cog):
    CHECK_LIST = ("Parameters", "Returns", "Examples")

    def __init__(self, worker):
        self.worker = worker
        self.data = {}

    def parse(self, doc: str) -> dict:
        wait, now, data = [False, ""], "", {}
        for line in doc.splitlines():
            if line in CHECK_LIST:
                wait = [True, line]
                now = line
            elif not line.startswith("---"):
                if wait[0]:
                    if now == "Examples":
                        data[now] += line + "\n"
                    else:
                        if now in data:
                            data[now] = []
                        data[now].append(
                            {
                                ""
                            }
                        )
                else:
                    data["description"] += line + "\n"
        return data

    @rtutil.Cog.event()
    async def on_command_add(self, data):
        self.data[] = self.parse(data["coro"].__doc__)
