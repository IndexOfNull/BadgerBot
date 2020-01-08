import asyncio

import discord
from discord.ext import commands

import functools

def discord_obj_tostring(obj):
    if isinstance(obj, discord.User) or isinstance(obj, discord.Member):
        return obj.name + "#" + obj.discriminator
    if isinstance(obj, discord.TextChannel):
        return "#" + obj.name
    if isinstance(obj, discord.Guild):
        return obj.name

#decorator to force commands to get confirmation from the invoking user
class ConfirmationFailed(Exception): pass
def require_confirmation():
    def wrapper(coro):
        @functools.wraps(coro)
        async def wrapped(cog, ctx, *args, **kwargs):
            # Some fancy boo stuff
            msg = await ctx.send(ctx.responses['verify_message'])
            allow, deny = ("✅", "❌")
            await msg.add_reaction(allow)
            await msg.add_reaction(deny)

            def check(reaction, user):
                return user == ctx.author and (str(reaction.emoji) == allow or str(reaction.emoji) == deny)

            try:
                reaction, user = await cog.bot.wait_for('reaction_add', timeout=5, check=check)
                if str(reaction.emoji) == deny:
                    await msg.edit(content=ctx.responses['verify_canceled'])
                    raise ConfirmationFailed("The confirmation was canceled")
            except asyncio.TimeoutError:
                await msg.edit(content=ctx.responses['verify_timeout'])
                raise ConfirmationFailed("The confirmation request timed out")
            else:
                await msg.edit(content=ctx.responses['verify_confirmed'])
                return await coro(cog, ctx, *args, **kwargs)
        return wrapped
    return wrapper