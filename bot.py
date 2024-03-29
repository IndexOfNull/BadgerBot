import discord
from discord.ext import commands

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sqlalchemy as sa
import asyncio

from utils import classes, data, checks, funcs, http, config
from utils.pagination import PaginationManager
import utils.messages.manager

modules = [
	"cogs.core",
	"cogs.util",
	"cogs.tags",
	"cogs.fun",
	"cogs.owner",
	"cogs.music"
] #What cogs to load

class BuddyBot(commands.Bot):

	def __init__(self, *args, **kwargs):
		command_prefix = commands.when_mentioned_or(";")
		help_command = classes.CustomHelpCommand()

		intents = discord.Intents.default()
		privileged_intents = kwargs.pop("privileged_intents", [])
		intents.members = ("members" in privileged_intents)
		intents.presences = ("presences" in privileged_intents)

		super().__init__(command_prefix = command_prefix, help_command = help_command, intents = intents, *args, **kwargs)
		self.prefix = ";"
		self.token = kwargs.pop("token")
		self.owner = None #Retrieved later in on_ready
		self.db_engine_uri = kwargs.pop("db_engine_uri")
		self.dev_mode = kwargs.pop("dev_mode", False)
		self.create_tables = kwargs.pop("create_tables", False)
		self.db_engine = create_engine(self.db_engine_uri)
		Session = sessionmaker(bind=self.db_engine)
		self.db = Session()
		self.remove_command('help')
		#Messages
		self.response_manager = utils.messages.manager
		#Init datamanager and register options
		self.datamanager = data.DataManager(self, False) #Tell it not to autopopulate prefixes, that will happen when the bot is ready.
		self.datamanager.register_option("lang", "en")
		self.datamanager.register_option("responses", "default")
		self.datamanager.register_option("prefix", self.prefix)
		self.pagination_manager = PaginationManager(self, stale_time=300)
		self.database_ping_interval = kwargs.pop("db_ping_interval", 28800/2) #28800 is the default wait_timeout value in MySQL. This will ping every 4 hours
		self.http_session = http.http_session
		self.been_ready = False #This will be set to true on the first on_ready call
		#Init global config
		config.create_tables = self.create_tables
		config.database = self.db

	async def database_ping_task(self):
		while True:
			try:
				self.db.execute("SELECT 1")
			except sa.exc.SQLAlchemyError as e:
				print("DATABASE PING ERROR:", e)
				await asyncio.sleep(60) #Retry again in 60 seconds.
				continue
			await asyncio.sleep(self.database_ping_interval)

	async def paginator_cleanup_task(self):
		while True:
			await asyncio.sleep(290)
			self.pagination_manager.clean_paginators()

	async def on_message(self, message):
		if message.author.bot:
			return
		await self.wait_until_ready()
		#discord.Message.options = self.datamanager.get_options(message.guild.id, basic=True)
		ctx = await self.get_context(message, cls=classes.CustomContext) #We can use this to subclass by adding the 'cls' kwarg
		if ctx.valid:
			ctx.injectcustom()
		await self.invoke(ctx)

	async def get_prefix(self, message):
		if not message.guild:
			return commands.when_mentioned_or(*[";"])(self, message)
		if not str(message.guild.id) in self.datamanager.prefixes.keys():
			prefixes = [self.prefix]
		else:
			prefixes = [self.datamanager.prefixes[str(message.guild.id)]]
		if message.content.split(" ")[0] == ";prefix":
			prefixes.append(self.prefix)
		return commands.when_mentioned_or(*prefixes)(self, message)

	def load_cogs(self, mods):
		finalstr = ""
		for cog in mods: #Iterate through all the cogs and load them
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
		#Cogs are done loading
		if not self.been_ready:
			self.responses = utils.messages.manager.build_responses() #Doing this later lets cogs add their own message keys
			if self.create_tables:
				config.declarative_base.metadata.create_all(self.db.bind) #Create the database tables if requested

	async def on_ready(self): #THIS MAY BE RUN MULTIPLE TIMES IF reconnect=True!
		if not self.been_ready:
			if self.database_ping_interval > 0:
				self.loop.create_task(self.database_ping_task())
			self.loop.create_task(self.paginator_cleanup_task())
		try:
			self.db.execute("SELECT * FROM server_options ORDER BY RAND() LIMIT 1") #Get a random server opt row as a sanity check. This is MySQL specific, so reformatting may be needed for other DBs
		except sa.exc.ProgrammingError:
			print("It appears that the database was not initialized properly. Try rerunning with --create-tables")
			exit()
		except:
			print("Something is wrong with the database. Ensure that you have entered the right info into the config.json file and try again.")
			exit()
		self.datamanager.refresh()
		self.been_ready = True
		#Print a nice hello message
		print("---[Ready]---")
		print("Logged in as:", self.user)
		print("Developer mode:", ("ENABLED" if self.dev_mode else "DISABLED"))
		print("Database Ping Interval: " + ((str(self.database_ping_interval) + " seconds") if self.database_ping_interval > 0 else "NEVER"))
		print("-------------")

	async def on_command_error(self, ctx, e):
		if ctx.ignore_errors is True:
			return
		if isinstance(e, commands.BadArgument) or isinstance(e, commands.MissingRequiredArgument):
			await ctx.send_help(ctx.command)
			return
		elif isinstance(e, commands.CommandNotFound): #Nonexistent command
			return
		elif isinstance(e, commands.CommandOnCooldown): #On cooldown
			s = e.retry_after
			h, rm = divmod(s,3600)
			m, seconds = divmod(rm,60)
			h,m = (round(h),round(m))
			m1 = m2 = ""
			if h > 0:
				m1 = "{0}h".format(h)
			if m > 0:
				m2 = "{0}h".format(m)
			after = "{0} {1} {2}s".format(m1,m2,round(seconds,1))
			after = after.strip()
			await ctx.send_response('error_cooldown', after)
			return
		elif type(e) is checks.MissingAdmin: #Admin only
			await ctx.send_response('error_adminonly')
			return
		elif type(e) is checks.MissingModerator: #Mod only
			await ctx.send_response('error_modonly')
			return
		elif isinstance(e, commands.BotMissingPermissions) or isinstance(e, checks.MissingAnyPermissions) or isinstance(e, commands.MissingPermissions) or isinstance(e, commands.MissingRole) or isinstance(e, commands.BotMissingAnyRole) or isinstance(e, commands.BotMissingRole): #missing permissions or roles
			await ctx.send(":closed_lock_with_key: " + str(e)) #Localization!
			return
		elif isinstance(e, commands.NoPrivateMessage): #Server only
			await ctx.send_response('error_serveronly')
			return
		elif isinstance(e, commands.PrivateMessageOnly): #DM only
			await ctx.send_response('error_dmonly')
			return
		elif isinstance(e, commands.DisabledCommand): #Disabled
			await ctx.send_response('error_cmddisabled')
			return
		elif isinstance(e, commands.NotOwner): #Owner only
			await ctx.send_response('error_owneronly')
			return
		elif isinstance(e, commands.NSFWChannelRequired): #NSFW only
			await ctx.send_response('error_nsfw')
			return
		elif isinstance(e, asyncio.TimeoutError):
			await ctx.send_response('command_timeout')
			return
		elif hasattr(e, 'original'):
			if isinstance(e.original, funcs.ConfirmationFailed): #We can ignore this as the decorator auto-edits the message
				return
			elif isinstance(e.original, asyncio.TimeoutError):
				await ctx.send_response('command_timeout')
				return
		await ctx.send("`Unhandled Error: " + str(e) + "`")
		raise e

	async def on_error(self, event, *args, **kwargs):
		if event == "on_message":
			message = args[0]
			await message.channel.send("Something went seriously wrong when processing your message. Something is probably wrong with the bot.")
		await super().on_error(event, *args, **kwargs)

	def run(self):
		#Load cogs
		self.load_cogs(modules)
		super().run(self.token)

	async def close(self):
		print("Closing")
		self.db.close()
		self.db_engine.dispose()
		await self.http_session.close()
		await super().close()
		pending = len(asyncio.Task.all_tasks())
		print("Cleaned up successfully. Waiting for %s tasks to finish." % pending)