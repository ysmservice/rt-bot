# RT - Web

import rtutil


web = rtutil.RTSanicServer("rt.web")


web.app.run(host="127.0.0.1", port=8080)
