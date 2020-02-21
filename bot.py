import discord
from discord.ext import commands

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa

import asyncio
import aiohttp
from aiohttp import web

from utils import classes, data, checks, funcs
import utils.messages.manager

import json

modules = [
	"cogs.profile",
	"cogs.tags",
	"cogs.core",
	"cogs.fun",
	"cogs.leveling",
	"cogs.owner"
] #What cogs to load

class BuddyBot(commands.Bot):

	def __init__(self, *args, **kwargs):
		command_prefix = commands.when_mentioned_or(";")
		help_command = classes.CustomHelpCommand()
		super().__init__(command_prefix = command_prefix, help_command = help_command, *args, **kwargs)
		self.prefix = ";"
		self.token = kwargs.pop("token")
		self.owner = None #Retrieved later in on_ready
		self.db_engine_uri = kwargs.pop("db_engine_uri")
		self.dev_mode = kwargs.pop("dev_mode", False)
		self.create_tables = kwargs.pop("create_tables", False)
		self.pool_recycle = kwargs.pop("pool_recycle", 0) #How long until we recycle long open connections.
		db_engine_kwargs = {}
		if self.pool_recycle != 0: db_engine_kwargs['pool_recycle'] = self.pool_recycle
		self.db_engine = create_engine(self.db_engine_uri, **db_engine_kwargs)
		Session = sessionmaker(bind=self.db_engine)
		self.db = Session()
		self.remove_command('help')
		#Messages
		self.responses = utils.messages.manager.responses
		#Init datamanager and register options
		self.datamanager = data.DataManager(self, False) #Tell it not to autopopulate prefixes, that will happen when the bot is ready.
		self.datamanager.register_option("lang", "en")
		self.datamanager.register_option("responses", "default")
		self.datamanager.register_option("prefix", self.prefix)
		self.web_secret = kwargs.pop("web_secret", None)


	def start_webserver(self):
		self.web_app = web.Application(middlewares=[self.web_keymiddleware])
		web_runner = web.AppRunner(self.web_app)
		#Register routes
		routes = [
			web.get('/broadcast', self.web_broadcast),
			web.get('/event', self.web_event)
		]
		self.web_app.add_routes(routes)
		#Run it
		self.loop.run_until_complete(web_runner.setup())
		web_site = web.TCPSite(web_runner)
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

	async def on_ready(self): #THIS MAY BE RUN MULTIPLE TIMES IF reconnect=True!
		try:
			self.db.execute("SELECT * FROM serveropts ORDER BY RAND() LIMIT 1") #Get a random server opt row as a sanity check. This is MySQL specific, so reformatting may be needed for other DBs
		except sa.exc.ProgrammingError:
			print("It appears that the database was not initialized properly. Try rerunning with --create-tables")
			exit()
		except:
			print("Something is wrong with the database. Ensure that you have entered the right info into the config.json file and try again.")
			exit()
		self.datamanager.refresh()
		#Print a nice hello message
		print("---[Ready]---")
		print("Logged in as:", self.user)
		print("Developer mode is " + ("ENABLED" if self.dev_mode else "DISABLED"))
		print("-------------")

	async def on_command_error(self, ctx, e):
		if isinstance(e, commands.BadArgument) or isinstance(e, commands.MissingRequiredArgument):
			await ctx.send_help(ctx.command)
		elif isinstance(e, commands.CommandNotFound): #Nonexistent command
			pass
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
		elif isinstance(e, commands.BotMissingPermissions) or isinstance(e, checks.MissingAnyPermissions) or isinstance(e, commands.MissingPermissions) or isinstance(e, commands.MissingRole) or isinstance(e, commands.BotMissingAnyRole) or isinstance(e, commands.BotMissingRole): #missing permissions or roles
			await ctx.send(":closed_lock_with_key: " + str(e))
		elif isinstance(e, commands.NoPrivateMessage): #Server only
			await ctx.send(ctx.responses['error_serveronly'])
		elif isinstance(e, commands.PrivateMessageOnly): #DM only
			await ctx.send(ctx.responses['error_dmonly'])
		elif isinstance(e, checks.MissingAdmin): #Admin only
			await ctx.send(ctx.responses['error_adminonly'])
		elif isinstance(e, checks.MissingModerator): #Mod only
			await ctx.send(ctx.responses['error_modonly'])
		elif isinstance(e, commands.DisabledCommand): #Disabled
			await ctx.send(ctx.responses['error_cmddisabled'])
		elif isinstance(e, commands.NotOwner): #Owner only
			await ctx.send(ctx.responses['error_owneronly'])
		elif isinstance(e, commands.NSFWChannelRequired): #NSFW only
			await ctx.send(ctx.responses['error_nsfw'])
		elif isinstance(e.original, funcs.ConfirmationFailed): #We can ignore this as the decorator auto-edits the message
			return
		else:
			await ctx.send("`Unhandled Error: " + str(e) + "`")

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
		self.start_webserver()
		super().run(self.token)

	async def close(self):
		self.db.close()
		self.db_engine.dispose()
		await super().close()
		pending = len(asyncio.Task.all_tasks())
		print("Cleaned up successfully. Waiting for %s tasks to finish." % pending)