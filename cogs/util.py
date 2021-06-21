import discord
from discord.ext import commands
from utils.funcs import emoji_format

class Object(object): pass

class FunCog(commands.Cog):

	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	async def emoji(self, ctx, *, emoji:discord.Emoji):
		emoji_str = "<{0}:{1}:{2}>".format("a" if emoji.animated else "", emoji.name, emoji.id)
		title = ("Emoji Info " + emoji_str) if emoji.is_usable() else "Emoji Info"
		embed = discord.Embed(title=title, type="Rich", color=discord.Color.blue())
		embed.set_thumbnail(url=emoji.url)
		embed.add_field(name="Name", value=emoji.name)
		embed.add_field(name="ID", value=emoji.id)
		embed.add_field(name="Non-Nitro Copy-Paste (For badge creation)", value="`" + emoji_format(emoji_str) + "`", inline=False)
		await ctx.send(embed=embed)

def setup(bot):
	bot.add_cog(FunCog(bot))