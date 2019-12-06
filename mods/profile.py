import discord
from discord.ext import commands

from mods.widget.badge import BadgeWidget
from mods.widget.classes import RenderManager

class ProfileCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.manager = RenderManager(self.bot.db, create_tables=True)
        self.badger = self.manager.register_widget(BadgeWidget)

    @commands.command()
    async def award(self, ctx):
        pass

    @commands.command()
    async def revoke(self, ctx):
        pass

    @commands.group()
    async def badge(self, ctx):
        pass

    @badge.command(aliases = ["add"])
    async def create(self, ctx):
        #self.badger.create_badge(ctx.guild.id, "TestBadge", ":test:", description="Just a test badge")
        pass

    @badge.command(aliases = ["remove"])
    async def delete(self, ctx):
        pass

    @badge.command()
    async def test(self, ctx):
        #self.badger.award_badge(ctx.guild.id, ctx.message.author.id, 1)
        pass

def setup(bot):
    bot.add_cog(ProfileCog(bot))