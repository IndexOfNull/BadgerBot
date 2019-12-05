import discord
from discord.ext import commands

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import asyncio

modules = [
    "mods.profile"
] #What cogs to load

class BuddyBot(commands.Bot):

    def __init__(self, *args, **kwargs):
        command_prefix = commands.when_mentioned_or(";")
        super().__init__(command_prefix = command_prefix, *args, **kwargs)
        self.token = kwargs.pop("token")
        self.owner = None #Retrieved later in on_ready
        self.db_engine_uri = kwargs.pop("db_engine_uri")
        self.dev_mode = kwargs.pop("dev_mode", False)
        self.db_engine = create_engine(self.db_engine_uri)
        Session = sessionmaker(bind=self.db_engine)
        self.db = Session()

    """async def command_help(self, ctx):
        if ctx.invoked_subcommand:
            cmd = ctx.invoked_subcommand
        else:
            cmd = ctx.command
        pages = await self.formatter.format_help_for(ctx, cmd)
        for page in pages:
            await ctx.channel.send"""

    async def on_message(self, message):
        ctx = await self.get_context(message) #We can use this to subclass by adding the 'cls' kwarg
        await self.invoke(ctx)

    async def on_ready(self):
        #Load cogs
        finalstr = ""
        for cog in modules: #Iterate through all the cogs and load them
            try:
                self.load_extension(cog)
            except Exception as e:
                finalstr += "Module: {0}\n{1}: {2}\n".format(cog,type(e).__name__,e)
        if finalstr != "": #Print cog errors if any have occured
            finalstr = finalstr[:-1]
            print('\n======COG ERRORS======')
            print(finalstr)
            print("======================\n\nWARNING: Some cogs failed to load! Some things may not function properly.\n")
        #Print a nice hello message
        print("---[Ready]---")
        print("Logged in as:", self.user)
        print("Developer mode is " + ("ENABLED" if self.dev_mode else "DISABLED"))
        print("-------------")

    def run(self):
        super().run(self.token)

    async def close(self):
        await super().close()
        self.db.close()
        self.db_engine.dispose()
        pending = len(asyncio.Task.all_tasks())
        print("Cleaned up successfully. Waiting for %s tasks to finish." % pending)