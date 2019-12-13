import discord
from discord.ext import commands

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import asyncio

from utils import classes, data

modules = [
    "mods.profile",
    "mods.tags"
] #What cogs to load

class BuddyBot(commands.Bot):

    def __init__(self, *args, **kwargs):
        command_prefix = commands.when_mentioned_or(";")
        help_command = classes.CustomHelpCommand()
        super().__init__(command_prefix = command_prefix, help_command = help_command, *args, **kwargs)
        self.token = kwargs.pop("token")
        self.owner = None #Retrieved later in on_ready
        self.db_engine_uri = kwargs.pop("db_engine_uri")
        self.dev_mode = kwargs.pop("dev_mode", False)
        self.create_tables = kwargs.pop("create_tables", False)
        self.db_engine = create_engine(self.db_engine_uri)
        Session = sessionmaker(bind=self.db_engine)
        self.db = Session()
        self.remove_command('help')
        #Init datamanager and register options
        self.datamanager = data.DataManager(self)
        #self.datamanager.register_option("test", "1234")
        #self.datamanager.register_option("lang", "en")

    async def on_message(self, message):
        if message.author.bot:
            return
        ctx = await self.get_context(message) #We can use this to subclass by adding the 'cls' kwarg
        await self.invoke(ctx)

    async def on_ready(self):
        #Load cogs
        finalstr = ""
        for cog in modules: #Iterate through all the cogs and load them
            try:
                self.load_extension(cog)
            except commands.ExtensionAlreadyLoaded:
                pass
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

    async def on_command_error(self, ctx, e):
        if isinstance(e, commands.BadArgument) or isinstance(e, commands.MissingRequiredArgument):
            await ctx.send_help(ctx.command)
        elif isinstance(e, commands.CommandNotFound):
            pass #I like this a bit more
            #await ctx.send(":mag_right: That command doesn't exist.")
        elif isinstance(e, commands.CommandOnCooldown):
            #Make this more comprehensive (e.retry_after)
            await ctx.send(":timer: That command is on cooldown.")
        elif isinstance(e, commands.BotMissingPermissions):
            #Make this more comprehensive (e.missing_perms)
            await ctx.send(":closed_lock_with_key: I don't have the necessary permissions to run your command.")
        elif isinstance(e, commands.BotMissingRole):
            #Make this more comprehensie (e.missing_role)
            await ctx.send(":no_entry: I don't have the necessary roles to run your command.")
        elif isinstance(e, commands.NoPrivateMessage):
            await ctx.send(":speech_balloon: Your command can only be used in servers.")
        else:
            await ctx.send("`Unhandled Error: " + str(e) + "`")

    def run(self):
        super().run(self.token)

    async def close(self):
        await super().close()
        self.db.close()
        self.db_engine.dispose()
        pending = len(asyncio.Task.all_tasks())
        print("Cleaned up successfully. Waiting for %s tasks to finish." % pending)