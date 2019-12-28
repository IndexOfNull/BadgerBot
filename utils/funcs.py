import discord
from discord.ext import commands

def discord_obj_tostring(obj):
    if isinstance(obj, discord.User) or isinstance(obj, discord.Member):
        return obj.name + "#" + obj.discriminator
    if isinstance(obj, discord.TextChannel):
        return "#" + obj.name
    if isinstance(obj, discord.Guild):
        return obj.name