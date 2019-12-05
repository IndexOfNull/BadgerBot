import discord
from discord.ext import commands

class ProfileCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx):
        await ctx.send("Hello from ProfileCog!")

def setup(bot):
    bot.add_cog(ProfileCog(bot))