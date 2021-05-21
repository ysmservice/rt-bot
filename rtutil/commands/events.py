# RT - Events

import discord

from .type_manager import TypeManager


tm = TypeManager()


# Workerにデータを転送するためのイベントを登録するやつ。
def add_event_hook(bot, queue):
	@bot.event
	async def on_ready():
		queue.put(["on_ready", None])

	@bot.event
	async def on_message(message):
		queue.put(["on_message", tm.message_to_dict(message)])

	def on_reaction(reaction, user, event_type):
		if isinstance(user, discord.User):
			member = discord.utils.get(reaction.message.guild.members, id=user.id)
		data = {
			"reaction": tm.reaction_to_dict(reaction),
			"uesr": tm.member_to_dict(member) if member else tm.user_to_dict(user)
		}
		queue.put(["on_reaction_" + event_type, data])

	@bot.event
	async def on_reaction_add(reaction, user):
		on_reaction(reaction, user, "add")

	@bot.event
	async def on_reaction_remove(reaction, user):
		on_reaction(reaction, user, "remove")
