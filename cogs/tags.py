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
    @commands.cooldown(1, 3, type=commands.BucketType.channel)
    async def tag(self, ctx, *, tag:str): #Get the content of a tag
        tag = self.get_tags(ctx, name=tag).first()
        if not tag:
            await ctx.send_response('tag_notfound')
            return
        await ctx.send(tag.content)

    @commands.command(aliases = ["maketag", "addtag"])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def createtag(self, ctx, name:str, *, content:str): #Create a tag
        #Check name and content length
        if len(name) > 100:
            await ctx.send_response('tag_lenlimits', "names", 100)
            return
        if len(content) > 500:
            await ctx.send_response('tag_lenlimits', "contents", 500)
            return
        tag_count = self.get_tags(ctx).count()
        if tag_count >= 15: #limit to 15 tags
            await ctx.send_response('tag_serverlimit')
            return
        exists = self.get_tags(ctx, name=name).first()
        if not exists:
            result = self.add_tag(ctx, name, content)
            if result:
                await ctx.send_response('tag_created')
            else:
                await ctx.send_response('tag_error', "creating")
        else:
            await ctx.send_response('tag_exists')

    @commands.command(aliases = ["deltag", "deletetag"])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def removetag(self, ctx, *, name:str): #Delete a tag
        tag = self.get_tags(ctx, name=name).first()
        if not tag:
            await ctx.send_response('tag_notfound')
            return
        result = self.remove_tag(ctx, name)
        if result:
            await ctx.send_response('zapped', name)
        else:
            await ctx.send_response('tag_error', "deleting")

    @commands.command(aliases = ["taglist", "listtag", "tagslist", "listtags"])
    @commands.guild_only()
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    async def tags(self, ctx): #list the tags
        line = "+ {0.name}\n"
        finalstr = "> __Tags__\n```diff\n"
        server_tags = self.get_tags(ctx)
        count = 0
        for row in server_tags:
            count += 1
            finalstr += line.format(row)
        if count == 0:
            finalstr = ctx.responses['tag_notags']
        else:
            finalstr += "```"
        await ctx.send(finalstr)

    @commands.command(aliases = ["changetag"])
    @commands.guild_only()
    @checks.is_admin()
    @commands.cooldown(1, 10, type=commands.BucketType.guild)
    async def updatetag(self, ctx, name:str, *, content:str): #Change the content of tag
        result = self.update_tag(ctx, name, content)
        if result:
            await ctx.send_response('tag_update')
        else:
            await ctx.send_response('tag_notfound')

def setup(bot):
    bot.add_cog(TagCog(bot))