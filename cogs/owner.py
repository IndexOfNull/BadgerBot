import discord
from discord.ext import commands

from utils import funcs

from sqlalchemy import Column, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
class BotOption(Base):
    __tablename__ = "botopts"
    option = Column(String(64), nullable=False, primary_key=True)
    value = Column(Text(), nullable=True)

class BotOwnerCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.keep_enabled = True
        self.db = self.bot.db
        if self.bot.create_tables:
            Base.metadata.create_all(self.db.bind)

    def set_value(self, key, value): #Updates a bot variable in the db (inserting when necessary)
        try:
            row = self.db.query(BotOption).filter_by(option=key).first()
            if row:
                row.value = value
            else:
                row = BotOption(option=key, value=value)
                self.db.add(row)
            self.db.commit()
            return row
        except Exception as e:
            self.db.rollback()
            raise e

    def get_value(self, **filters):
        try:
            row = self.db.query(BotOption).filter_by(**filters).first()
            return row
        except Exception as e:
            self.db.rollback()
            raise e
    
    @commands.Cog.listener()
    async def on_ready(self):
        activity_str = self.get_value(option="activity")
        if activity_str: #If there's a row
            activity_type, name = activity_str.value.split(";", 1) #Split by the first ;
            if activity_type == "nothing":
                activity = None
            else:
                activity = discord.Activity(name=name, type=getattr(discord.ActivityType, activity_type))
            await self.bot.change_presence(activity=activity)

    @commands.command(aliases=["setactivity"], hidden=True)
    @commands.is_owner()
    async def activity(self, ctx, activity_type:str=None, *, text:str=""):
        if not activity_type:
            await ctx.send_response('general_valid_options', "playing, listening and watching")
            return
        activity_type = activity_type.lower()
        if not activity_type in ("playing", "listening", "watching"):
            await ctx.send_response('general_valid_options', "playing, listening and watching")
            return
        activity = discord.Activity(name=text, type=getattr(discord.ActivityType, activity_type))
        await self.bot.change_presence(activity=activity)
        self.set_value("activity", activity_type + ";" + text)
        await ctx.send_response('setactivity_success')

    @commands.command(hidden=True)
    @commands.is_owner()
    @funcs.require_confirmation()
    async def reloadmodule(self, ctx, *, module:str):
        try:
            self.bot.reload_extension(module)
        except Exception as e:
            await ctx.send_response('module_fail')
            raise e
        else:
            await ctx.send_response('module_reloaded', module)

    @commands.command(hidden=True)
    @commands.is_owner()
    @funcs.require_confirmation()
    async def unloadmodule(self, ctx, *, module:str):
        try:
            self.bot.unload_extension(module)
        except Exception as e:
            await ctx.send_response('module_fail')
            raise e
        else:
            await ctx.send_response('module_unloaded', module)

    @commands.command(hidden=True)
    @commands.is_owner()
    @funcs.require_confirmation()
    async def loadmodule(self, ctx, *, module:str):
        try:
            self.bot.load_extension(module)
        except Exception as e:
            await ctx.send_response('module_fail')
            raise e
        else:
            await ctx.send_response('module_loaded', module)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def exec(self, ctx, *, code:str): #with great power comes great destructiveness
        code = code.strip("` py")
        # Make an async function with the code and `exec` it
        exec(
            f'async def __ex(bot, ctx, message, server, channel, author): ' +
            ''.join(f'\n {l}' for l in code.split('\n'))
        )
        # Get `__ex` from local variables, call it and return the result
        try:
            result = await locals()['__ex'](self.bot, ctx, ctx.message, ctx.guild, ctx.channel, ctx.author)
        except Exception as e:
            await ctx.send("Error: " + str(e))
        else:
            await ctx.send("`{0}`".format(result))

def setup(bot):
    bot.add_cog(BotOwnerCog(bot))