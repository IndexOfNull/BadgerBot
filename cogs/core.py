from discord.ext import commands
from utils import checks
import inspect

class CoreCommandsCog(commands.Cog):

	def __init__(self, bot):
		self.bot = bot
		self.datamanager = bot.datamanager
		self.keep_enabled = True

	@commands.command()
	@commands.guild_only()
	@commands.cooldown(1, 10, type=commands.BucketType.guild)
	async def prefix(self, ctx, prefix:str=None):
		if not prefix:
			await ctx.send_response('prefix', ctx.options['prefix'].data)
		else:
			if not checks.is_admin(return_predicate=True)(ctx): #should error if they aren't an admin
				return
			if len(prefix) > 8:
				await ctx.send_responses('prefix_limit', 8)
				return
			if not prefix == ctx.options['prefix'].data: #No need to bother if it's being set to the same thing
				self.datamanager.set_option(ctx.guild.id, "prefix", prefix)
				self.datamanager.prefixes[str(ctx.guild.id)] = prefix
			await ctx.send_responses('prefix_set', prefix)

	#This doesn't properly update cooldowns. For now its best to omit a cooldown as can be confusing without explicit messages.
	@commands.command()
	#@commands.cooldown(1, 3, type=commands.BucketType.user)
	async def page(self, ctx, page:int):
		user_paginator = self.bot.pagination_manager.get_user(ctx.author.id)
		if user_paginator:
			paginator, stored_context, reinvoke, _ = user_paginator
			target_command = stored_context.command
			can_run = await target_command.can_run(stored_context)
			on_cooldown = target_command.is_on_cooldown(ctx)
			if on_cooldown: #TODO: make a custom error so we can tell people to specifically slow down for paging.
				raise commands.CommandOnCooldown(None, target_command.get_cooldown_retry_after(ctx))
			if can_run:
				paginator.current_page = page-1
				if inspect.iscoroutinefunction(reinvoke):
					await reinvoke(ctx, paginator)
				else:
					reinvoke(ctx, paginator)

	@commands.command(aliases=['cmds', 'commands'])
	async def help(self, ctx, command:str=""):
		command = command.replace(".", " ")
		if command:
			cmd = self.bot.get_command(command)
			if cmd:
				await ctx.send_help(cmd)
				return
		await ctx.send("https://github.com/IndexOfNull/BadgerBot/blob/master/commands.txt")

def setup(bot):
	bot.add_cog(CoreCommandsCog(bot))