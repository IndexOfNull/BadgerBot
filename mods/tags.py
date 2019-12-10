from discord.ext import commands
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TIMESTAMP
from sqlalchemy import Column, Text, String, BigInteger, Integer

Base = declarative_base()
class TagEntry(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    server_id = Column(BigInteger, nullable=False)
    name = Column(String(128, collation="utf8mb4_unicode_ci"), nullable=False)
    content = Column(Text(collation="utf8mb4_unicode_ci"), nullable=False)

class TagCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        if bot.create_tables:
            Base.metadata.create_all(bot.db.bind)

    @commands.group()
    async def tag(self, ctx, tag:str):
        pass

    @tag.command()
    async def create(self, ctx, name:str, content:str):
        pass

    @tag.command()
    async def remove(self, ctx, name:str):
        pass

def setup(bot):
    bot.add_cog(TagCog(bot))