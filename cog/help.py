# RT - Help

import rtutil


class Help(metaclass=rtutil.Cog):
    CHECK_LIST = ("Parameters", "Returns", "Examples")

    def __init__(self, worker):
        self.worker = worker
        self.data = {}

    def parse(self, doc: str) -> dict:
        wait, now, data = [False, ""], "", {}
        now_parameter = ""
        for line in doc.splitlines():
            if line.startswith("    "):
                line = line[4:]
            if line in CHECK_LIST:
                if now != "Examples" and now:
                    data[now][now_parameter]["description"] = data[now][now_parameter]["description"][:-1] # noqa
                    data["description"] = data["description"][1:-3]
                wait = [True, line]
                now = line
            elif not line.startswith("---"):
                if wait[0]:
                    if not line or line.count(" ") == len(line):
                        continue
                    if now == "Examples":
                        data[now] = data.get(now, "") + line + "\n"
                    else:
                        if now not in data:
                            data[now] = []
                        if line.startswith("    "):
                            line = line[4:]
                            n = (data[now][now_parameter].get("description", "")
                                 + line + "\n")
                            data[now][now_parameter]["description"] = n
                        else:
                            splited = line.split()
                            now_parameter = splited[0]
                            if splited[2][-1] == ",":
                                splited[2] = splited[2][:-1]
                                default = True
                            else:
                                default = False
                            data[now].append(
                                {
                                    "name": splited[0],
                                    "description": "",
                                    "type": splited[2],
                                    "default": splited[3] if default else None
                                }
                            )
                            now_parameter = len(data[now]) - 1
                            if now_parameter:
                                data[now][now_parameter-1]["description"] = data[now][now_parameter-1]["description"][:-1] # noqa
                else:
                    data["description"] = data.get("description", "") + line + "\n"
        return data

    @rtutil.Cog.event()
    async def on_command_add(self, data):
        self.data[] = self.parse(data["coro"].__doc__)

    def parse(self, doc: str) -> dict:
        wait, now, data = [False, ""], "", {}
        now_parameter = ""
        for line in doc.splitlines():
            if line.startswith("    "):
                line = line[4:]
            if line in CHECK_LIST:
                wait = [True, line]
                now = line
            elif not line.startswith("---"):
                if wait[0]:
                    if now == "Examples":
                        data[now] += line + "\n"
                    else:
                        if now in data:
                            data[now] = {}
                        if now.startswith("    "):
                            n = line + "\n"
                            data[now][now_parameter]["description"] += n
                        else:
                            splited = line.split()
                            now_parameter = splited[0]
                            if splited[2][-1] == ",":
                                splited[2] = splited[2][:-1]
                                default = True
                            else:
                                default = False
                            data[now][now_parameter] = {
                                "description": "",
                                "type": splited[2],
                                "default": splited[3] if default else None
                            }
                else:
                    data["description"] += line + "\n"
        return data
