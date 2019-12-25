from discord.ext import commands


class OptionsCog(commands.Cog):

	def __init__(self, bot):
		self.bot = bot
		self.datamanager = bot.datamanager

	@commands.command()
	async def prefix(self, ctx, prefix:str=None):
		if not prefix:
			await ctx.send(ctx.responses['prefix'].format(ctx.options['prefix'].data))
		else:
			if len(prefix) > 8:
				await ctx.send(ctx.responses['prefix_limit'].format(8))
				return
			if not prefix == ctx.options['prefix'].data: #No need to bother if it's being set to the same thing
				self.datamanager.set_option(ctx.guild.id, "prefix", prefix)
				self.datamanager.prefixes[str(ctx.guild.id)] = prefix
			await ctx.send(ctx.responses['prefix_set'].format(prefix))


def setup(bot):
	bot.add_cog(OptionsCog(bot))