from discord.ext import commands
from utils import checks

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
			await ctx.send(ctx.responses['prefix'].format(ctx.options['prefix'].data))
		else:
			if not checks.is_admin(return_predicate=True)(ctx): #should error if they aren't an admin
				return
			if len(prefix) > 8:
				await ctx.send(ctx.responses['prefix_limit'].format(8))
				return
			if not prefix == ctx.options['prefix'].data: #No need to bother if it's being set to the same thing
				self.datamanager.set_option(ctx.guild.id, "prefix", prefix)
				self.datamanager.prefixes[str(ctx.guild.id)] = prefix
			await ctx.send(ctx.responses['prefix_set'].format(prefix))

	@commands.command()
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