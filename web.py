# RT - Web

import rtutil


web = rtutil.RTSanicServer("rt.web", logging_level=rtutil.logging.DEBUG)


web.app.run(host="0.0.0.0", port=5000)
