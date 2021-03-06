import discord
from discord.ext import commands

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa

import asyncio
import aiohttp
from aiohttp import web

from utils import classes, data, checks, funcs, http
import utils.messages.manager
import json

modules = [
	"cogs.profile",
	"cogs.tags",
	"cogs.core",
	"cogs.fun",
	"cogs.leveling",
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
		self.web_enable = kwargs.pop("web_enable", False)
		self.web_secret = kwargs.pop("web_secret", None)
		self.web_ip = kwargs.pop("web_ip", "0.0.0.0")
		self.web_port = kwargs.pop("web_port", "8080")
		self.database_ping_interval = kwargs.pop("db_ping_interval", 28800/2) #28800 is the default wait_timeout value in MySQL. This will ping every 4 hours
		self.http_session = http.http_session
		self.been_ready = False #This will be set to true on the first on_ready call

	async def database_ping_task(self):
		while True:
			try:
				self.db.execute("SELECT 1")
			except sa.exc.SQLAlchemyError as e:
				print("DATABASE PING ERROR:", e)
				await asyncio.sleep(60) #Retry again in 60 seconds.
				continue
			await asyncio.sleep(self.database_ping_interval)

	def start_webserver(self):
		self.web_app = web.Application(middlewares=[self.web_keymiddleware])
		self.web_runner = web.AppRunner(self.web_app)
		#Register routes
		routes = [
			web.get('/broadcast', self.web_broadcast),
			web.get('/event', self.web_event)
		]
		self.web_app.add_routes(routes)
		#Run it
		self.loop.run_until_complete(self.web_runner.setup())
		web_site = web.TCPSite(self.web_runner, host=self.web_ip, port=self.web_port)
		self.loop.run_until_complete(web_site.start())

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

	async def on_ready(self): #THIS MAY BE RUN MULTIPLE TIMES IF reconnect=True!
		if not self.been_ready and self.database_ping_interval > 0:
			self.loop.create_task(self.database_ping_task())
		try:
			self.db.execute("SELECT * FROM serveropts ORDER BY RAND() LIMIT 1") #Get a random server opt row as a sanity check. This is MySQL specific, so reformatting may be needed for other DBs
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
		print("Internal Webserver Enabled: " + str(self.web_enable))
		if self.web_enable:
			print("Webserver IP/Port: " + self.web_ip + ":" + self.web_port)
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
			await ctx.send(ctx.responses['error_cooldown'].format(after))
			return
		elif type(e) is checks.MissingAdmin: #Admin only
			await ctx.send(ctx.responses['error_adminonly'])
			return
		elif type(e) is checks.MissingModerator: #Mod only
			await ctx.send(ctx.responses['error_modonly'])
			return
		elif isinstance(e, commands.BotMissingPermissions) or isinstance(e, checks.MissingAnyPermissions) or isinstance(e, commands.MissingPermissions) or isinstance(e, commands.MissingRole) or isinstance(e, commands.BotMissingAnyRole) or isinstance(e, commands.BotMissingRole): #missing permissions or roles
			await ctx.send(":closed_lock_with_key: " + str(e))
			return
		elif isinstance(e, commands.NoPrivateMessage): #Server only
			await ctx.send(ctx.responses['error_serveronly'])
			return
		elif isinstance(e, commands.PrivateMessageOnly): #DM only
			await ctx.send(ctx.responses['error_dmonly'])
			return
		elif isinstance(e, commands.DisabledCommand): #Disabled
			await ctx.send(ctx.responses['error_cmddisabled'])
			return
		elif isinstance(e, commands.NotOwner): #Owner only
			await ctx.send(ctx.responses['error_owneronly'])
			return
		elif isinstance(e, commands.NSFWChannelRequired): #NSFW only
			await ctx.send(ctx.responses['error_nsfw'])
			return
		elif hasattr(e, 'original'):
			if isinstance(e.original, funcs.ConfirmationFailed): #We can ignore this as the decorator auto-edits the message
				return
		await ctx.send("`Unhandled Error: " + str(e) + "`")
		raise e

	async def on_error(self, event, *args, **kwargs):
		if event == "on_message":
			message = args[0]
			await message.channel.send("Something went seriously wrong when processing your message. Something is probably wrong with the bot.")
		await super().on_error(event, *args, **kwargs)

	@web.middleware
	async def web_keymiddleware(self, request, handler):
		if self.web_secret:
			if 'Authorization' in request.headers:
				key = request.headers['Authorization']
			elif 'secret' in request.query:
				key = request.query['secret']
			else:
				resp = {"status": "error", "error": "No secret passed."}
				return web.Response(status=403, text=json.dumps(resp))
			if not key == self.web_secret:
				resp = {"status": "error", "error": "Invalid secret."}
				return web.Response(status=403, text=json.dumps(resp))
		resp = await handler(request)
		return resp

	async def web_broadcast(self, request):
		pcog = self.get_cog("ProfileCog")
		if not pcog:
			r = {"status": "error", "error": "The profile cog (and thus the widget manager) is not loaded."}
			return web.Response(status=503, text=json.dumps(r))
		if not 'event' in request.query or not 'payload' in request.query:
			r = {"status": "error", "error": "You must pass an event and a payload"}
			return web.Response(status=406, text=json.dumps(r))
		else:
			pcog.manager.broadcast(request.query['event'], request.query['payload'])
			r = {"status": "good"}
			return web.Response(status=200, text=json.dumps(r))

	async def web_event(self, request):
		pcog = self.get_cog("ProfileCog")
		if not pcog:
			r = {"status": "error", "error": "The profile cog (and thus the widget manager) is not loaded."}
			return web.Response(status=503, text=json.dumps(r))
		if not 'event' in request.query or not 'payload' in request.query:
			r = {"status": "error", "error": "You must pass an event and a payload"}
			return web.Response(status=406, text=json.dumps(r))
		else:
			try:
				result = pcog.manager.fire_event(request.query['event'], **request.query) #Request params get converted to kwargs
			except KeyError:
				resp = {"status": "error", "error": "The specified event does not exist."}
				return web.Response(status=406, text=json.dumps(resp))
			r = {"status": "good", "result": result}
			return web.Response(status=200, text=json.dumps(r))

	def run(self):
		#Load cogs
		self.load_cogs(modules)
		if self.web_enable: self.start_webserver()
		super().run(self.token)

	async def close(self):
		print("Closing")
		self.db.close()
		self.db_engine.dispose()
		if self.web_enable: await self.web_runner.cleanup()
		await self.http_session.close()
		await super().close()
		pending = len(asyncio.Task.all_tasks())
		print("Cleaned up successfully. Waiting for %s tasks to finish." % pending)