import discord
from discord.ext import commands
from random import randint, choice
import random

from PIL import Image

from utils import funcs
from io import BytesIO

class Object(object): pass

class FunCog(commands.Cog):

	def __init__(self, bot):
		self.bot = bot
		self.zalgo = Object()
		###Zalgo constants
		self.zalgo.CHAR_UP = ['\u030D', '\u030E', '\u0304', '\u0305', '\u033F',
					'\u0311', '\u0306', '\u0310', '\u0352', '\u0357',
					'\u0351', '\u0307', '\u0308', '\u030A', '\u0342',
					'\u0343', '\u0344', '\u034A', '\u034B', '\u034C',
					'\u0303', '\u0302', '\u030C', '\u0350', '\u0300',
					'\u0301', '\u030B', '\u030F', '\u0312', '\u0313',
					'\u0314', '\u033D', '\u0309', '\u0363', '\u0364',
					'\u0365', '\u0366', '\u0367', '\u0368', '\u0369',
					'\u036A', '\u036B', '\u036C', '\u036D', '\u036E',
					'\u036F', '\u033E', '\u035B', '\u0346', '\u031A']
		self.zalgo.CHAR_MID = ['\u0315', '\u031B', '\u0340', '\u0341', '\u0358',
					'\u0321', '\u0322', '\u0327', '\u0328', '\u0334',
					'\u0335', '\u0336', '\u034F', '\u035C', '\u035D',
					'\u035E', '\u035F', '\u0360', '\u0362', '\u0338',
					'\u0337', '\u0361', '\u0489']
		self.zalgo.CHAR_DOWN = ['\u0316', '\u0317', '\u0318', '\u0319', '\u031C',
					'\u031D', '\u031E', '\u031F', '\u0320', '\u0324',
					'\u0325', '\u0326', '\u0329', '\u032A', '\u032B',
					'\u032C', '\u032D', '\u032E', '\u032F', '\u0330',
					'\u0331', '\u0332', '\u0333', '\u0339', '\u033A',
					'\u033B', '\u033C', '\u0345', '\u0347', '\u0348',
					'\u0349', '\u034D', '\u034E', '\u0353', '\u0354',
					'\u0355', '\u0356', '\u0359', '\u035A', '\u0323']
		self.zalgo.ZALGO_POS = ("up","down","mid")
		self.zalgo.ZALGO_CHARS = {"up":self.zalgo.CHAR_UP,"mid":self.zalgo.CHAR_MID,"down":self.zalgo.CHAR_DOWN}

	@commands.command(aliases=["coin"])
	async def flip(self, ctx):
		side = randint(0,5999) #Check if it will land on its side. Credit: https://journals.aps.org/pre/abstract/10.1103/PhysRevE.48.2547
		if side == 0:
			await ctx.send_response("coin_3")
			return
		side = str(randint(1,2))
		await ctx.send_response("coin_" + side)

	@commands.command(aliases=["rockpaperscissors","saishowagujankenpon"])
	async def rps(self, ctx, weapon:str):
		emoji = {"rock": ":fist:", "paper": ":newspaper:", "scissors": ":scissors:"}
		weapon = weapon.lower()
		if weapon in ["rock", "r"]:
			w = "rock"
		elif weapon in ["paper", "p"]:
			w = "paper"
		elif weapon in ["scissors", "s"]:
			w = "scissors"
		else:
			await ctx.send_response('general_valid_options', "[r]ock, [p]aper, or [s]cissors.")
			return
		botchoice = choice(["rock", "paper", "scissors"])
		formatted = emoji[botchoice] + " " + botchoice.capitalize()
		if botchoice == w:
			await ctx.send_response('rps_tie', formatted)
		elif ( botchoice == "rock" and w == "paper" ) or ( botchoice == "scissors" and w == "rock" ) or ( botchoice == "paper" and w == "scissors" ):
			await ctx.send_response('rps_win', formatted)
		else:
			await ctx.send_response('rps_lose', formatted)

	@commands.command(aliases=["rollthedice","rtd","roll"])
	async def dice(self, ctx, sides:int=6):
		if sides > 100:
			await ctx.send_response('dice_limit', 100)
			return
		if sides < 2:
			await ctx.send_response('dice_limit_lower', 2)
			return
		side = randint(1, sides)
		await ctx.send(":game_die: " + str(side))

	@commands.command(aliases=["iqcounter"])
	async def iq(self, ctx, user:discord.Member=None):
		if user is None:
			user = ctx.author
		iq = randint(0, 200)
		await ctx.send_response('iq', user, iq)

	@commands.command(name="8ball", aliases=["eightball", "fortune"])
	async def eball(self, ctx, *, question:str):
		response = choice(ctx.get_response('8ball_responses'))
		await ctx.send(response)

	@commands.command(name="zalgo")
	async def zalgotext(self, ctx, *, text:str): #Based off of https://gist.github.com/MetroWind/1401473/4631da7a4540a63e72701792a4aa0262acc7d397
		result = []
		for char in text:
			ZalgoCounts = {"up": 0, "down": 0, "mid": 0}
			for pos in self.zalgo.ZALGO_POS:
				ZalgoCounts[pos] = random.randint(0, 7)
			result.append(char)
			for pos in self.zalgo.ZALGO_POS:
				c = random.sample(self.zalgo.ZALGO_CHARS[pos],ZalgoCounts[pos])
				result.append(''.join(c))
		await ctx.send(''.join(result))

	@commands.command(aliases = ["ship"])
	@commands.cooldown(1, 3, type=commands.BucketType.user)
	async def marry(self, ctx, waifu:discord.Member, husbando:discord.Member):
		#add restriction against marrying self
		if waifu == husbando:
			await ctx.send_response('marry_notself')
			return
		imageformat, imagesize = "png", 64 #Each image will be 64x64
		u1icon = waifu.avatar_url_as(format = imageformat, static_format = imageformat, size = imagesize)
		u2icon = husbando.avatar_url_as(format = imageformat, static_format = imageformat, size = imagesize)
		u1iconbytes = BytesIO(await u1icon.read())
		u2iconbytes = BytesIO(await u2icon.read())
		u1img = Image.open(u1iconbytes)
		u2img = Image.open(u2iconbytes)
		heart = Image.open("resources/img/heart.png")
		canvas = Image.new("RGBA", (198, 64), (0, 0, 0, 0)) #64*3 = 192, add six for margins
		canvas.paste(u1img, (0, 0))
		canvas.paste(heart, (67, 0))
		canvas.paste(u2img, (134, 0))
		b = funcs.img_to_bytesio(canvas, "PNG")
		f = discord.File(b, filename="married.png")
		#make child name
		names = [waifu.display_name, husbando.display_name]
		finalname = ""
		for name in names:
			splitname = name.split(" ")
			if len(splitname) == 1:
				#finalname += splitname[0][ :(int(len(splitname[0])/2)) ] #Get half of the string. This is messy
				finalname += splitname[0][ :(randint(0, len(splitname[0]))) ]
			else:
				if randint(0, 1) == 0:
					finalname += ("").join(splitname[ :int(len(splitname)/2) ]) + " "
				else:
					finalname += ("").join(splitname[ int(len(splitname)/2): ]) + " "
		finalname = '"' + finalname.rstrip() + '"'
		message = ctx.get_response('marry_message').format(waifu, husbando, finalname)
		await ctx.send(message, file=f)

def setup(bot):
	bot.add_cog(FunCog(bot))