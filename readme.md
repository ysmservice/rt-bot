[![Discord Bots](https://top.gg/api/widget/status/716496407212589087.svg)](https://top.gg/bot/716496407212589087) [![Discord Bots](https://top.gg/api/widget/servers/716496407212589087.svg)](https://top.gg/bot/716496407212589087) ![Discord](https://img.shields.io/discord/718641964672876614?label=support&logo=discord)
# RT Bot
This is the RT Bot of Discord's Bot.  
RT is a feature-rich bot with features that most bots have.  
It also has features that other bots don't have.  
Connect to RT, Discord's Bot account, to start RT's service.  
It also communicates with `rt-backend` via WebSocket for web authentication and so on.  
If you don't know about RT, have a look at [here](https://rt-bot.com).  
(日本語版のreadmeは[こちら](https://github.com/RT-Team/rt-bot/blob/main/readme.ja.md))

## LICENSE
`BSD 4-Clause License` (The `LICENSE` file has more details.)

## CONTRIBUTION
See `contributing.md`.

## Installation.
## Dependencies.
Required.

* Python 3.10
* MySQL or MariaDB.
* Everything in `requirements.txt`.
* Run `rt-backend` if you want to use functions that require a backend such as authentication.
### Startup procedure: 1.
1. install required items with `pip install -r requirements.txt` 2.
2. write necessary TOKEN etc. to `auth.json` referring to `auth.template.json`. 3.
Put the `rt-module` repository in `rtlib` and name the folder `rt_module`. 4.
4. run the program in the `rt-backend` repository.
   (This is optional and you need to do it if you want to run something that requires a backend such as authentication. 5.)
Run the tests with `python3 main.py test`.
   (In this case, TOKEN will be the one in the `test` key of `auth.json`.)

(In this case, TOKEN is the one in the key of `test` in `auth.json`.) * Read `readme.md` in `cogs/tts` if you want to run the readout.
### Run production.
The startup command is `sudo -E python3 main.py production` and you need `auth.json` TOKEN for `production`.
