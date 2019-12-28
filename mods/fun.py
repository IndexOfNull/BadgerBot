import discord
from discord.ext import commands
from random import randint, choice
import random


class FunCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["coin"])
    async def flip(self, ctx):
        side = randint(0,5999) #Check if it will land on its side. Credit: https://journals.aps.org/pre/abstract/10.1103/PhysRevE.48.2547
        if side == 0:
            await ctx.send(ctx.responses["coin_3"])
            return
        side = str(randint(1,2))
        await ctx.send(ctx.responses["coin_" + side])

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
            await ctx.send(ctx.responses["general_valid_options"].format("[r]ock, [p]aper, or [s]cissors."))
            return
        botchoice = choice(["rock", "paper", "scissors"])
        formatted = emoji[botchoice] + " " + botchoice.capitalize()
        if botchoice == w:
            await ctx.send(ctx.responses['rps_tie'].format(formatted))
        elif ( botchoice == "rock" and w == "paper" ) or ( botchoice == "scissors" and w == "rock" ) or ( botchoice == "paper" and w == "scissors" ):
            await ctx.send(ctx.responses['rps_win'].format(formatted))
        else:
            await ctx.send(ctx.responses['rps_lose'].format(formatted))

    @commands.command(aliases=["rollthedice","rtd","roll"])
    async def dice(self, ctx, sides:int=6):
        if sides > 100:
            await ctx.send(ctx.responses['dice_limit'].format(100))
            return
        if sides < 2:
            await ctx.send(ctx.responses['dice_limit_lower'].format(2))
            return
        side = randint(1, sides)
        await ctx.send(":game_die: " + str(side))

    @commands.command(aliases=["iqcounter"])
    async def iq(self, ctx, user:discord.Member=None):
        if user is None:
            user = ctx.author
        iq = randint(0, 200)
        await ctx.send(ctx.responses['iq'].format(user, iq))        

def setup(bot):
    bot.add_cog(FunCog(bot))