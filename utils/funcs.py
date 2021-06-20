import asyncio
import discord
import functools
from io import BytesIO
import re
import regex
import emoji

def clamp(n, smallest, largest):
    return max(smallest, min(n, largest))

def discord_obj_tostring(obj):
    if isinstance(obj, discord.User) or isinstance(obj, discord.Member):
        return obj.name + "#" + obj.discriminator
    if isinstance(obj, discord.TextChannel):
        return "#" + obj.name
    if isinstance(obj, discord.Guild):
        return obj.name

#decorator to force commands to get confirmation from the invoking user
class ConfirmationFailed(Exception): pass
def require_confirmation(*, warning=None):
    def wrapper(coro):
        @functools.wraps(coro)
        async def wrapped(cog, ctx, *args, **kwargs):
            # Some fancy boo stuff
            msg = ctx.responses['verify_message']
            if warning:
                msg += "\n**WARNING: " + warning + "**" #Needs a localization string
            msg = await ctx.send(msg)
            allow, deny = ("✅", "❌")
            await msg.add_reaction(allow)
            await msg.add_reaction(deny)

            def check(reaction, user): #The reaction is for the right message, from the executor, and is either an allow or deny
                return reaction.message.id == msg.id and user == ctx.author and ( str(reaction.emoji) == allow or str(reaction.emoji) == deny )

            try:
                reaction, user = await ctx.bot.wait_for('reaction_add', timeout=20, check=check)
                if str(reaction.emoji) == deny:
                    await msg.edit(content=ctx.responses['verify_canceled'])
                    await msg.delete(delay=5)
                    raise ConfirmationFailed("The confirmation was canceled")
            except asyncio.TimeoutError:
                await msg.edit(content=ctx.responses['verify_timeout'])
                raise ConfirmationFailed("The confirmation request timed out")
            else:
                await msg.edit(content=ctx.responses['verify_confirmed'])
                await msg.delete(delay=5)
                return await coro(cog, ctx, *args, **kwargs)
        return wrapped
    return wrapper

def sizeof_fmt(num):
    suffix = "B"
    for unit in ['','K','M','G','T','P','E','Z']:
        if abs(num) < 1000.0:
            return "%d%s%s" % (num, unit, suffix)
        num /= 1000.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

emoji_regex = re.compile(r'\<:(\w*?):(\d*?)\>')

def emoji_escape(text: str):
    return re.sub(r'\[;(\w*?);(\d*?)\]', r'<:\1:\2>', text)

def emoji_format(text: str):
    return re.sub(emoji_regex, r'[;\1;\2]', text)

#Returns a list of emojis contained in the passed text. custom_emoji will include discord custom emoji.
#Setting tuple to True will turn each list item into a tuple of (match, is_custom)
def extract_emoji(text, *, custom_emoji=False, as_tuple=False):
    emoji_or_unicode = regex.compile(r"\<:\w*?:\d*?\>|\X")
    emoji_list = [] #Tuple (emoji, is_custom)
    data = regex.findall(emoji_or_unicode, text)
    for match in data:
        if any(char in emoji.UNICODE_EMOJI['en'] for char in match):
            ins = (match, False) if as_tuple else match
            emoji_list.append(ins)
        elif re.match(emoji_regex, match) and custom_emoji:
            ins = (match, True) if as_tuple else match
            emoji_list.append(ins)
    return emoji_list

def async_partial(f, *args):
   async def f2(*args2):
       result = f(*args2, *args)
       if asyncio.iscoroutinefunction(f):
           result = await result
       return result
   return f2
