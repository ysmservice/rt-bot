# RT - Web

import rtutil


web = rtutil.RTSanicServer("rt.web", logging_level=rtutil.logging.DEBUG)


web.app.run(host="127.0.0.1", port=8080)
