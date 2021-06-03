from functools import update_wrapper
from sqlalchemy.orm.query import Query as saQuery
import math
import time

from utils.funcs import clamp

# Takes a list-like object or a SQLAlchemy query and splits it up
class Paginator(): #Maybe split this up into a baseclass, list pager, and database pager?

    #This is a needlessly complicated system for pagination
    #On the upside, it should be pretty memory efficient, as it prepares the data as needed without keeping it around
    #A caveat to this is that if you need to use pages more than once you should *absolutely* store the result of get_pages into a variable.

    def __init__(self, l, *, items_per_page=10, page=0):
        self.items_per_page = items_per_page
        self.page_obj = l #This will transparently move into self._page_obj after validation
        self._current_page = page

    @property
    def current_page(self):
        return self._current_page

    @current_page.setter
    def current_page(self, page):
        self._current_page = clamp(page, 0, self.page_count-1)

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
        self._current_page = 0
        #Possible values: "db", "list"

    @property
    def page_count(self):
        if self.type == "list":
            return math.ceil(len(self._page_obj) / self.items_per_page) #Be generous and call 1.1 pages 2 :)
        if self.type == "db":
            return math.ceil(self.page_obj.count() / self.items_per_page) #Same here

    @property
    def item_count(self):
        if self.type == "list":
            return len(self._page_obj)
        if self.type == "db":
            return self.page_obj.count()

    def get_current_page(self):
        return self.get_page(self._current_page)

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

# Keeps track of paginator objects for discord users, enabling stateful paging.
class PaginationManager():

    def __init__(self, bot, *, stale_time=300):
        self.bot = bot
        self.stale_time = stale_time
        self._users = {} # user id -> (paginator, ctx, reinvoke, updated_at)
        
    #Always returns an existing or new paginator adjusted for the current invoked command in ctx.
    def ensure_paginator(self, *, user_id, ctx, obj, reinvoke, **kwargs):
        user_paginator = self.get_user(user_id)
        if user_paginator:
            paginator, stored_context, reinvoke2, updated_at = user_paginator
            if stored_context.command != ctx.command: #If this command does not match the last used one, update the paginator to match the command
                paginator = Paginator(obj, **kwargs)
                self.update_user(user_id=user_id, ctx=ctx, paginator=paginator, reinvoke=reinvoke)
        else: #If our user doesn't have a paginator, make one!
            paginator = Paginator(obj, **kwargs)
            self.update_user(user_id=user_id, ctx=ctx, paginator=paginator, reinvoke=reinvoke)
            paginator, stored_context, reinvoke2, updated_at = self.get_user(user_id)
        return paginator, stored_context, reinvoke2, updated_at

    def get_user(self, user_id):
        if user_id in self._users:
            return self._users[user_id]

    def update_user(self, *, user_id, ctx, paginator, reinvoke):
        self._users[user_id] = (paginator, ctx, reinvoke, int(time.time()))

    def remove_user(self, user_id):
        del self._users[user_id]

    def clean_paginators(self):
        current_time = time.time()
        to_remove = []
        for user_id, data in self._users.items():
            if current_time - data[3] >= self.stale_time:
                to_remove.append(user_id)
        for user_id in to_remove:
            self.remove_user(user_id)