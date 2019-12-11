from discord.ext import commands
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TIMESTAMP
from sqlalchemy import Column, Text, String, BigInteger, Integer

import datetime

from utils import checks

Base = declarative_base()
class TagEntry(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True)
    server_id = Column(BigInteger, nullable=False)
    name = Column(String(128, collation="utf8mb4_unicode_ci"), nullable=False)
    content = Column(Text(collation="utf8mb4_unicode_ci"), nullable=False)
    created_on = Column(TIMESTAMP, default=datetime.datetime.now()) #a timestamp to keep track of when the row was added

class TagCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        if bot.create_tables:
            Base.metadata.create_all(bot.db.bind)

    def get_tags(self, ctx, **kwargs):
        result = self.db.query(TagEntry).filter_by(server_id=ctx.guild.id, **kwargs)
        return result

    def add_tag(self, ctx, name, content):
        try:
            tag = TagEntry(server_id=ctx.guild.id, name=name, content=content)
            self.db.add(tag)
            self.db.commit()
            return tag
        except Exception as e:
            self.db.rollback()
            raise e

    def remove_tag(self, ctx, name):
        try:
            result = self.db.query(TagEntry).filter_by(server_id=ctx.guild.id, name=name).delete()
            self.db.commit()
            return result
        except Exception as e:
            self.db.rollback()
            raise e

    def update_tag(self, ctx, name, content):
        try:
            row = self.db.query(TagEntry).filter_by(server_id=ctx.guild.id, name=name).first()
            if not row:
                return None
            row.content = content
            self.db.commit()
            return row
        except Exception as e:
            self.db.rollback()
            raise e

    @commands.command()
    @commands.guild_only()
    async def tag(self, ctx, *, tag:str): #Get the content of a tag
        tag = self.get_tags(ctx, name=tag).first()
        if not tag:
            await ctx.send(":grey_question: There doesn't appear to be a tag with that name.")
            return
        await ctx.send(tag.content)

    @commands.command(aliases = ["maketag", "addtag"])
    @commands.guild_only()
    @checks.is_admin()
    async def createtag(self, ctx, name:str, *, content:str): #Create a tag
        #Check name and content length
        if len(name) > 100:
            await ctx.send(":red_circle: Tag names cannot be over 100 characters. Please shorten it.")
            return
        if len(content) > 500:
            await ctx.send(":red_circle: A tag's contents cannot be over 500 characters. Please shorten it.")
            return
        tag_count = self.get_tags(ctx).count()
        if tag_count >= 15: #limit to 15 tags
            await ctx.send(":red_circle: Servers can only have up to 15 tags.")
            return
        exists = self.get_tags(ctx, name=name).first()
        if not exists:
            result = self.add_tag(ctx, name, content)
            if result:
                await ctx.send(":speech_balloon: Your tag has been created successfully.")
            else:
                await ctx.send(":red_circle: Something went wrong while creating your badge.")
        else:
            await ctx.send(":red_circle: There is already a tag with that name.")

    @commands.command(aliases = ["deltag"])
    @commands.guild_only()
    @checks.is_admin()
    async def removetag(self, ctx, *, name:str): #Delete a tag
        tag = self.get_tags(ctx, name=name).first()
        if not tag:
            await ctx.send(":grey_question: There doesn't appear to be a tag with that name")
            return
        result = self.remove_tag(ctx, name)
        if result:
            await ctx.send(":cloud_lightning: " + name + " has been zapped.")
        else:
            await ctx.send(":red_circle: Something went wrong while deleting your tag.")

    @commands.command(aliases = ["taglist", "listtag", "tagslist", "listtags"])
    @commands.guild_only()
    async def tags(self, ctx): #list the tags
        line = "+ {0.name}\n"
        finalstr = "> __Tags__\n```diff\n"
        server_tags = self.get_tags(ctx)
        count = 0
        for row in server_tags:
            count += 1
            finalstr += line.format(row)
        if count == 0:
            finalstr = ":white_sun_small_cloud: This server has no tags."
        else:
            finalstr += "```"
        await ctx.send(finalstr)

    @commands.command(aliases = ["changetag"])
    @commands.guild_only()
    @checks.is_admin()
    async def updatetag(self, ctx, name:str, *, content:str): #Change the content of tag
        result = self.update_tag(ctx, name, content)
        if result:
            await ctx.send(":envelope_with_arrow: Your tag has been updated successfully!")
        else:
            await ctx.send(":grey_quesiton: It doesn't look like there's a tag with that name.")

def setup(bot):
    bot.add_cog(TagCog(bot))