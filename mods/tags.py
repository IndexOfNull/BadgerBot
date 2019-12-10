from discord.ext import commands

class TagCog(commands.Cog):

    def __init__(self, bot)
        self.bot = bot

    @commands.group()
    async def tag(self, ctx, tag:str)
        pass

    @tag.command()
    async def create(self, ctx, name:str, content:str):
        pass

    @tag.command()
    async def remove(self, ctx, name:str):
        pass

def setup(bot):
    bot.add_cog(TagCog(bot))