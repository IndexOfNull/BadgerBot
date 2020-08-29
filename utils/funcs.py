import asyncio

import discord
from discord.ext import commands

import functools

from io import BytesIO

from sqlalchemy.orm.query import Query as saQuery
import math

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

def img_to_bytesio(img, *args):
    b = BytesIO()
    img.save(b, *args)
    b.seek(0)
    return b

class Paginator():

    #This is a needlessly complicated system for pagination
    #On the upside, it should be pretty memory efficient, as it prepares the data as needed without keeping it around
    #A caveat to this is that if you need to use pages more than once you should *absolutely* store the result of get_pages into a variable.

    def __init__(self, l, *, items_per_page=10):
        self.items_per_page = items_per_page
        self.page_obj = l #This will transparently move into self._page_obj after validation

    @property
    def page_obj(self):
        return self._page_obj

    @page_obj.setter
    def page_obj(self, val):
        if not isinstance(val, list) and not isinstance(val, saQuery):
            raise TypeError("You must pass a list or SQLAlchemy ORM Query!")
        if isinstance(val, saQuery):
            self.type = "db"
        if isinstance(val, list):
            self.type = "list"
        self._page_obj = val
        #Possible values: "db", "list"

    @property
    def page_count(self):
        if self.type == "list":
            return math.ceil(len(self._page_obj) / self.items_per_page) #Be generous and call 1.1 pages 2 :)
        if self.type == "db":
            return math.ceil(self.page_obj.count() / self.items_per_page) #Same here

    def get_pages(self, pages): #Will accept positive integers or positive slices with a step of 1
        #Making sure everything is the right type because we are nice
        if isinstance(pages, int): 
            if pages < 0:
                raise Exception("You may not use a negative index with the Paginator object!")
            pages = range(pages, pages+1) #Convert to a list if we just have a single int
        elif isinstance(pages, slice):
            if pages.step:
                if pages.step != 1:
                    raise Exception("You may not use any non-one slice steps with the Paginator object!")
            pages = range(pages.start, pages.stop)
        else:
            slice_start = min(pages)
            slice_end = max(pages)
            pages = range(slice_start, slice_end+1) #Gotta make it inclusive. Note that this behavior is only exhibited when using lists. Slices will still work how Pythoners expect them to.
        #pages should be a range at this point
        if self.type == "list":
            return [self._page_obj[(page * self.items_per_page) : (page * self.items_per_page) + self.items_per_page] for page in pages] #Oh god...
        if self.type == "db": #this should be fun (12:05 AM)
            bulk_obj = self._page_obj.slice((pages.start * self.items_per_page), (pages.stop * self.items_per_page)).all()
            return [bulk_obj[(page * self.items_per_page) : (page * self.items_per_page) + self.items_per_page] for page in range(0, pages.stop - pages.start)]

    def get_page(self, page): #Because we are nice, again...
        return self.get_pages(page)[0]

    #__iter__ may come one day. But I can't be bothered with caching and doing it right

    def __getitem__(self, index):
        if isinstance(index, slice) or isinstance(index, int):
            return self.get_pages(index)
        raise TypeError("You must pass an index or a positive slice with an unspecified step (or 1)!")