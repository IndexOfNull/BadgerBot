#This module makes use of the PyNaCl library, you may remove PyNaCl if you decide not to enable this. This module will also likely depend on libopus, so have that installed.
#Also huge thanks to this gist: https://gist.github.com/vbe0201/ade9b80f2d3b64643d854938d40a0a2d
import discord
from discord.ext import commands
import asyncio
from async_timeout import timeout
import itertools
import random
import typing

import functools
import youtube_dl
import aiohttp
from urllib.parse import urlparse
from io import BytesIO

from cogs.music import fftools
from cogs.music import checks as musicchecks
from utils import checks

import json, os
file_path = os.path.dirname(os.path.realpath(__file__))

"""
When writing this module I encountered the interesting mechanics of the asyncio ThreadPoolExecutor,
which is what is used pretty heavily throughout this software. Asyncio in Python versions
below 3.8 sets the max worker threads to os.cpu_count() times five. This means that the executor
could make 20 threads on my Macbook that has only 2 cores and 4 threads! Even worse, I usually deploy my bots
to a 12 core, 24 thread server. That means that the ThreadPoolExecutor would happily use 120 threads! To add even
more insult to injury, it appears that the the max worker count must be hit before threads are reused, so there's
really only going up in terms thread count. This wouldn't be so bad if Python didn't have a GIL, but whatever.

If you don't want to run into this, run the bot on Python 3.8. It will set the max threads to 32 or os.cpu_count()+4, whichever is less.
I may add an option to change this if I can figure out how.
"""

"""
TODO:

- Fix "Twitch:stream" source (maybe)
- Source restriction
"""

#Maybe implement a song class to hold info about a song (like source, who requested it, other metadata, etc)

mcog = None

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}
YTDL = youtube_dl.YoutubeDL(YTDL_OPTIONS)

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

class VoiceError(commands.CommandError): pass
class NotInSameVoiceChannel(commands.CommandError): pass
class BotNotInVoice(commands.CommandError): pass
class UserNotInVoice(commands.CommandError): pass
class YTDLError(commands.CommandError): pass
class EmptyQueue(commands.CommandError): pass
class MissingPerms(commands.CommandError): pass
class AudioInfoTransformer(discord.AudioSource):

    def __init__(self, original):
        if not isinstance(original, discord.AudioSource):
            raise TypeError('expected AudioSource not {0.__class__.__name__}.'.format(original))
        
        self.original = original
        self._ms_read = 0

    @property
    def head(self): #Returns the track head in milliseconds
        return self._ms_read

    def is_opus(self):
        return self.original.is_opus()

    def cleanup(self):
        self.original.cleanup()

    def read(self):
        a = self.original.read()
        if self._ms_read == 0 and len(a) == 0: #If we hit the end of the buffer and we haven't read anything
            raise EOFError("Audio stream ended without reading any data.")
        self._ms_read += 20 #20 is the default discord.py FRAME_LENGTH (see Encoder in discord/opus.py)
        return a

class SongQueue(asyncio.Queue): #A "FIFO" queue that has some LIFO elements
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

    def __delitem__(self, item): #idk if this supports slices but i don't care
        del self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        random.shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]

    def _putleft(self, item):
        self._queue.appendleft(item)

    def putleft_nowait(self, item):
        """Put an item into the left of the queue without blocking.

        If no free slot is immediately available, raise QueueFull.
        """
        if self.full():
            raise asyncio.queues.QueueFull
        self._putleft(item)
        self._unfinished_tasks += 1
        self._finished.clear()
        self._wakeup_next(self._getters)

class Song():

    def __init__(self, source, ctx:commands.Context=None, ytdl_info={}):
        self.source = source
        self.ctx = None
        self.requester = None
        if ctx:
            self.ctx = ctx
            self.requester = ctx.author

        self.ytdl_info = ytdl_info
        self.uploader = ytdl_info.get("uploader")
        self.uploader_url = ytdl_info.get("uploader_url")
        self.title = ytdl_info.get("title")
        self.thumbnails = ytdl_info.get("thumnails")
        self.thumbnail = ytdl_info.get("thumbnail")
        self.duration = ytdl_info.get("duration")
        self.extractor = ytdl_info.get("extractor")
        self.url = ytdl_info.get('webpage_url')

    @staticmethod
    def format_timebar(current=None, duration=None, *, length=17, dash='-', dot='🔵', unknown="Unknown"):
        if not duration or not current:
            s = unknown.center(length)
            s = s.replace(' ', dash)
            return s
        time_segments = duration/length #How much time each "dash" should represent
        index, remainder = divmod(current, time_segments)
        index = int(index)
        s = dash * length #Create the line
        s = s[:index] + dot + s[index + 1:] #Insert our dot
        return s

    def get_queue_entry(self):
        s = ""
        if self.title:
            s += "`" + self.title + "` "
        if self.duration:
            s += "(" + self.parse_duration(self.duration) + ")"
        else:
            s += "(" + self.ctx.responses['music_unknownduration'] + ")" #Yes, doing localization this way means that if the servers responses change, this will not
        if self.requester:
            s += " | " + self.ctx.responses['music_requestedby'] + ": " + self.requester.mention
        return s

    def get_embed(self):
        embed = discord.Embed(description='```yaml\n{0}\n```'.format(self.title),
                               color=discord.Color.from_rgb(233, 160, 63))

        if self.requester:
            embed.set_author(name=self.ctx.responses['music_nowplaying'], icon_url=self.requester.avatar_url_as(size=128))
        else:
            embed.title = self.ctx.responses['music_nowplaying']

        if isinstance(self.source, AudioInfoTransformer): #If we even have access to the current head
            bar = '`' + self.parse_duration(self.source.head/1000) + '` ' #Get the number of seconds passed
            if not self.duration:
                bar += '/ `' + self.ctx.responses['music_unknownduration'] + '`'
            else:
                bar += self.format_timebar(self.source.head/1000, self.duration) + ' `' + self.parse_duration(self.duration) + '`'
            bar += ' '
            #bar += 'Unknown' if not self.duration else self.parse_duration(self.duration) #Get the duration if possible, otherwise just say its unkown
            embed.add_field(name=self.ctx.responses['music_timebar'], value=bar)

        if self.uploader and self.uploader_url:
            embed.add_field(name=self.ctx.responses['music_uploader'], value='[{0}]({1})'.format(self.uploader, self.uploader_url))
        elif self.uploader or self.uploader_url:
            embed.add_field(name=self.ctx.responses['music_uploader'], value=(self.uploader + '\n' if self.uploader else '') + ('[' + self.uploader_url + ']' if self.uploader_url else ''), inline=False)
        
        if self.url:
            embed.add_field(name=self.ctx.responses['music_source'], value='[Click]({0})'.format(self.url))

        embed.add_field(name=self.ctx.responses['music_requestedby'], value=self.requester.mention)
        if self.thumbnail:
            embed.set_thumbnail(url=self.thumbnail)
        if self.extractor:
            if not self.extractor == 'generic':
                embed.set_footer(text=self.ctx.responses['music_from'].format(self.extractor.capitalize()))
            else:
                embed.set_footer(text=self.ctx.responses['music_fromgeneric']) 

        return embed

    @staticmethod
    def parse_duration(duration: int):
        minutes, seconds = divmod(duration, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        duration = []
        if days > 0:
            duration.append('{:n}'.format(int(days)))
            duration.append('{:02n}'.format(int(hours)))
            duration.append('{:02n}'.format(int(minutes)))
            duration.append('{:02n}'.format(int(seconds)))
        elif hours > 0:
            duration.append('{:n}'.format(int(hours)))
            duration.append('{:02n}'.format(int(minutes)))
            duration.append('{:02n}'.format(int(seconds)))
        else:
            duration.append('{:n}'.format(int(minutes)))
            duration.append('{:02n}'.format(int(seconds)))

        return ':'.join(duration)

    def __repr__(self):
        if self.title:
            return self.title
        else:
            return str(self.source)


class VoiceState(): #Responsible for managing all audio activity in a guild

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self._bot = ctx.bot
        self.parent = ctx.cog

        self.current = None
        self.voice = None #This will get set later by the actual music cog
        self.next_event = asyncio.Event() #Event to tell audio coroutine when it needs to move on to the next song
        self.audio_player = self._bot.loop.create_task(self.audio_player_task())
        self.song_queue = SongQueue()

        self.loop = False #Loop the queue? This will be further implemented later
        self.skips = set()
        #Flags
        self._paused = False #Keep track of if we should move the queue along.
        self._keep_skips = False #Flag to tell the after_handler not to discard skips
        self._keep_current = False #Flag to tell the after_handler not to set self.current = None
        self._waiting = False
        self._expect_skip = False #To be set whenever after_handler is called in an expected manner

    @property
    def is_playing(self): #Check if we are playing anything
        if self.voice: #Have to do this to be save that we have a VoiceClient instance.
            return self.current and self.voice.is_playing() #if there is a voice instance, check if it is playing anything
        return False

    @property
    def is_empty(self): #Check if the queue and playing are empty (awaiting a song)
        return not self.is_playing and ( len(self.song_queue) == 0 and not self.current)

    @property
    def paused(self):
        return self._paused

    @property
    def skips_required(self): #How many skips are required, returns None if not in a channel
        if not self.voice: #Make sure we actually have a voice state
            return None
        if not self.voice.channel: #Make sure we are connected
            return None
        member_count = len(self.voice.channel.members) - 1 #Number of users (minus the bot, of course)
        if member_count <= 1:
            return 1
        else:
            return member_count // 2 #One half of the users, leaning towards the smaller side

    def __del__(self): #This is a catch to prevent leaks, THIS SHOULD (IDEALLY) NEVER BE CALLED!
        self.audio_player.cancel() #Make sure we stop the audio player task when we clean up

    async def audio_player_task(self):
        while True:
            self.next_event.clear() #Reset the next flag
            self._waiting = False

            #Make sure that we are still playing stuff, otherwise disconnect after some time
            if not self.loop:
                try:
                    async with timeout(100):
                        self.current = await self.song_queue.get() #Get a song from the queue with a timeout of 180, otherwise disconnect
                except asyncio.TimeoutError:
                    self._bot.loop.create_task(self.close(True))
                    return
                
            #Play the stuff
            self.voice.play(self.current.source, after=self.after_handler) #This is non-blocking
            await self.next_event.wait() #Wait for the next event to be triggered

    def after_handler(self, error=None): #callback for when the current playing song finishes
        if error:
            if isinstance(error, EOFError):
                self.ctx.bot.loop.create_task(self.ctx.send(self.ctx.responses['music_endedbeforestart']))
            else:
                self.ctx.bot.loop.create_task(self.ctx.send('`' + str(error) + '`'))
        else:
            if not self._expect_skip and isinstance(self.current.source, AudioInfoTransformer):
                if self.current.duration:
                    if self.current.duration - (self.current.source.head / 1000) > 10: #If we end more than 10 seconds early and we weren't expecting a skip
                        self.ctx.bot.loop.create_task(self.ctx.send(self.ctx.responses['music_endedearly']))
        self._expect_skip = False        
        self._waiting = True
        if self._paused: #Do nothing if the queue is paused, this may have to be moved to the bottom in the future
            return
        if not self._keep_skips:
            self.skips.clear()
        if not self._keep_current:
            self.current = None
        self.next_event.set()            
        """self.current = None #Unset the current song (this will be set back in audio_player_task if there is another queued item)
        self.skips.clear() #Clear all votes to skip
        self.next_event.set()"""

    def resume(self): #Resume the current song and queue
        self._paused = False #Lets hope it doesn't error i guess ¯\_(ツ)_/¯, worst case we can manually clear skips and whatnot, but this is more consistent
        if self._waiting:
            self._expect_skip = True
            self.after_handler()
        else:
            self.voice.resume() #Only resume if we are actually resuming the same track, otherwise it will create a weird sounding blip.
        
    def pause(self): #Pause the current song and queue
        self.voice.pause()
        self._paused = True

    def skip(self):
        self._expect_skip = True
        self.voice.stop() #This stops the current song, do not be confused. This also calls the "after" callback set in self.voice.play()

    async def close(self, timeout=False): #Stop audio and disconnect
        self.song_queue.clear()
        if self.voice:
            self._expect_skip = True
            self.voice.stop()
            await self.voice.disconnect() #Close our connection
            self.voice = None #Destroy our connection
        if self.audio_player:
            self.audio_player.cancel()
        if timeout:
            self._bot.loop.create_task(self.parent.unregister_voice_state(self.ctx, auto_close=False))

class MusicCog(commands.Cog):

    def __init__(self, bot):
        print("WARNING: The music cog is, while functional, experimental and not without problems. You can track its progress on GitHub.")
        self.bot = bot
        self.voice_states = {}
        self.allowed_sources = ('youtube', 'soundcloud', 'vimeo', 'discord')

        if not self.bot.been_ready:
            self.add_responses()
            self.bot.datamanager.register_option('dj_role', '0')

        recommended_demuxers = ('h264', 'h265', 'mp3', 'aac', 'dash', 'webm_dash_manifest', 'matroska,webm')
        missing_demuxers = []
        demuxers = fftools.get_supported_formats()
        for demuxer in recommended_demuxers:
            if demuxer in demuxers:
                if not demuxers[demuxer][0]:
                    missing_demuxers.append(demuxer)
        if missing_demuxers:
            j = ";".join(missing_demuxers)
            print("You are missing demuxing support for the following formats, some sources may not work properly: " + j)

    def add_responses(self):
        with open(os.path.join(file_path, "responses.json"), 'r') as f:
            s = json.loads(f.read())
            self.bot.response_manager.add_response_set(s)

    async def ytdl_search(self, search):
        loop = self.bot.loop

        partial = functools.partial(YTDL.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)
        
        if data is None:
            raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        if 'entries' not in data:
            process_info = data
        else:
            process_info = None
            for entry in data['entries']:
                if entry:
                    process_info = entry
                    break

            if process_info is None:
                raise YTDLError('Couldn\'t find anything that matches `{}`'.format(search))

        webpage_url = process_info['webpage_url']
        partial = functools.partial(YTDL.extract_info, webpage_url, download=False)
        processed_info = await loop.run_in_executor(None, partial)

        if processed_info is None:
            raise YTDLError('Couldn\'t fetch `{}`'.format(webpage_url))

        if 'entries' not in processed_info:
            info = processed_info
        else:
            info = None
            while info is None:
                try:
                    info = processed_info['entries'].pop(0)
                except IndexError:
                    raise YTDLError('Couldn\'t retrieve any matches for `{}`'.format(webpage_url))
        if info['extractor'] == 'generic' and 'discord' in self.allowed_sources:
            parsed_url = urlparse(info['url'])
            if not parsed_url.netloc == "cdn.discordapp.com": #If it is a non-discord generic source
                raise YTDLError('Source not in sources whitelist.')
        elif info['extractor'] not in self.allowed_sources:
            raise YTDLError('Source not in sources whitelist.')
        return info

    async def remove_duplicates(self, index: int, queue: asyncio.Queue): #removes duplicates of a certain item in the queue
        #this is inefficient; O(n^2) worst case, O(n log n) best case (I think, could still be totally wrong)
        reference = queue[index]
        duplicate_indices = []
        for i, item in enumerate(queue):
            if i == index: #Don't dedupe the reference item
                continue
            if item is reference: #Dedupe if they are literally the same
                duplicate_indices.append(i)
            if item.url == reference.url: #Dedupe if the urls are the same
                duplicate_indices.append(i)
        amount = len(duplicate_indices)
        if amount == 0:
            return queue, 0
        while len(duplicate_indices) > 0:
            del queue[duplicate_indices[0]]
            duplicate_indices = [x-1 for x in duplicate_indices] #Recompute indices since they've all shifted down one
            duplicate_indices.pop(0)
        return queue, amount

    def get_voice_state(self, ctx: commands.Context): #Typing in Python? What!
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(ctx)
            self.voice_states[ctx.guild.id] = state
        return state

    async def cog_check(self, ctx: commands.Context):
        if ctx.guild is None:
            raise commands.NoPrivateMessage()
        return True

    async def cog_before_invoke(self, ctx: commands.Context): #Get ourselves a music context! (Only accessable throughout this cog)
        ctx.voice_state = self.get_voice_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, e):
        ctx.ignore_errors = True
        if isinstance(e, BotNotInVoice):
            await ctx.send(ctx.responses['music_botnotinvoice'])
        elif isinstance(e, EmptyQueue):
            await ctx.send(ctx.responses['music_emptyqueue'])
        elif isinstance(e, UserNotInVoice):
            await ctx.send(ctx.responses['music_usernotinvoice'])
        elif isinstance(e, NotInSameVoiceChannel):
            await ctx.send(ctx.responses['music_notinsamechannel'])
        elif isinstance(e, VoiceError):
            await ctx.send(ctx.responses['music_voiceerror'])
        elif isinstance(e, YTDLError):
            await ctx.send(ctx.responses['music_ytdlerror'])
        elif isinstance(e, commands.MissingAnyRole):
            await ctx.send(ctx.responses['music_noperms'])
        elif isinstance(e, MissingPerms):
            await ctx.send(ctx.responses['music_botmissingperms'])
        else:
            ctx.ignore_errors = False
            return

    async def unregister_voice_state(self, id: typing.Union[int, commands.Context], *, auto_close=True):
        if isinstance(id, commands.Context):
            id = id.guild.id
        if auto_close:
            state = self.voice_states.get(id)
            await state.close()
        del self.voice_states[id]

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after): #Removes the users vote and recomputes the number of needed votes 
        """
        ! This triggers when some MOVES/DISCONNECTS from a channel AND if we have a state !
        - If it is the bot's state that has changed, we check if it is still in a channel, if not, cleanup
        - If it is a user's state that has changed, we check to see if they are moving into the same channel
            as the bot (maybe it got summoned away), if not, discard any votes to skip they have.
        """
        if after.channel == before.channel: #We only want to detect when a member moves or leaves, so we can ignore all other updates
            return
        state = self.voice_states.get(member.guild.id)
        if not state:
            return #Do nothing if there is no voice state for the guild
        if member == self.bot.user:
            if after.channel is None: #If it is the bot and if it left (this should catch all disconnects not already handled)
                await self.unregister_voice_state(member.guild.id) #Unregister the voice state if we unexpectedly disconnect
                return
        else: #Not the bot moving
            if not state.voice:
                return
            if not after.channel == state.voice.channel:
                state.skips.discard(member.id) #Discard the users vote if they are moving out of the bots channel

    @commands.command(name="join", invoke_without_subcommand=True)
    @musicchecks.has_music_perms()
    async def _join(self, ctx: commands.Context):
        channel = ctx.author.voice.channel
        perms = channel.permissions_for(ctx.guild.me)
        if not perms.connect:
            raise MissingPerms('The bot does not have permission to connect to the specified VoiceChannel')
        if ctx.voice_state.voice: #If we have an existing connection, move it! This needs some permission checks
            await ctx.voice_state.voice.move_to(channel)
            return
        ctx.voice_state.voice = await channel.connect()
        if ctx.command is self.bot.get_command("join"):
            await ctx.send(ctx.responses['music_hello'])

    @commands.command(aliases=['voteskip'])
    async def skip(self, ctx):
        #Check if they have already voted

        #THESE CHECKS SHOULD MAKE THERE WAY INTO A before_invoke DECORATED FUNCTION!11!1
        """if not ctx.voice_state.is_playing:
            await ctx.send("Bot must be playing in order to skip.") #Add localization string for this later
            return"""
        if ctx.voice_state.is_empty:
            await ctx.send(ctx.responses['music_emptyqueue'])
            return
        if ctx.author.id in ctx.voice_state.skips:
            await ctx.send(ctx.responses['music_alreadyvoted'])
            return

        ctx.voice_state.skips.add(ctx.author.id)
        if len(ctx.voice_state.skips) >= ctx.voice_state.skips_required:
            ctx.voice_state.skip()
            await ctx.send(ctx.responses['music_skipped'])
            return
        await ctx.send(ctx.responses['music_voted'].format(len(ctx.voice_state.skips), ctx.voice_state.skips_required))

    @commands.command(name="pause", aliases=["stop"], invoke_without_subcommand=True)
    @musicchecks.has_music_perms()
    async def _pause(self, ctx: commands.Context):
        if ctx.voice_state.is_playing:
            ctx.voice_state.pause()
            await ctx.send(ctx.responses['music_paused'])
            return
        await ctx.send(ctx.responses['music_notplaying'])
    
    @commands.command(name="resume", invoke_without_subcommand=True)
    @musicchecks.has_music_perms()
    async def _resume(self, ctx: commands.Context):
        if ctx.voice_state.is_playing:
            await ctx.send(ctx.responses['music_alreadyplaying'])
            return
        if ctx.voice_state.is_empty:
            await ctx.send(ctx.responses['music_emptyqueue'])
            return
        ctx.voice_state.resume()
        await ctx.send(ctx.responses['music_resumed'])
        return
        
    @commands.command(name="leave", invoke_without_subcommand=True)
    @musicchecks.has_music_perms()
    async def _leave(self, ctx: commands.Context):
        if not ctx.voice_state.voice: #Check if we are connected, if not, throw an error
            raise BotNotInVoice("Cannot leave unless connected to a channel.")
        await self.unregister_voice_state(ctx, auto_close=True)

    @commands.command(aliases=['dedupe', 'deduplicate'])
    @musicchecks.has_music_perms()
    async def removedupes(self, ctx):
        if len(ctx.voice_state.song_queue) >= 1: #Just skip the actual dedupe process if there is only one song in the queue
            current_start = 0
            while current_start < len(ctx.voice_state.song_queue): #Doing it this way because changing list sizes in for loops scares me (and python sometimes)
                await self.remove_duplicates(current_start, ctx.voice_state.song_queue) #This is done in place, so who cares
                current_start += 1
        await ctx.send(ctx.responses['music_deduped'])

    @commands.command()
    @musicchecks.has_music_perms()
    async def leavecleanup(self, ctx):
        connected_users = ctx.voice_client.channel.members
        remove_indices = []
        for i, song in enumerate(ctx.voice_state.song_queue):
            if song.requester not in connected_users:
                remove_indices.append(i)
        removed = len(remove_indices)
        while len(remove_indices) > 0:
            del ctx.voice_state.song_queue[remove_indices[0]]
            remove_indices.pop(0)
            remove_indices = [x-1 for x in remove_indices]
        await ctx.send(ctx.responses['music_leavecleanup'].format(removed))

    @commands.command(name="play")
    @musicchecks.has_music_perms()
    async def _play(self, ctx, *, search:str=None):
        joined = False
        if not ctx.voice_state.voice: #Join if we aren't already connected
            await ctx.invoke(self._join)
            joined = True
        if search:
            await self.ensure_same_voice_channel(ctx)
            async with ctx.typing():
                info = await self.ytdl_search(search)
                try:
                    source = AudioInfoTransformer(discord.FFmpegOpusAudio(info['url'], **FFMPEG_OPTIONS))
                except Exception as e:
                    raise e
                else:
                    song = Song(source, ctx, info)

                    ctx.voice_state.song_queue.put_nowait(song)
                    await ctx.send(ctx.responses['music_queued'].format(str(song)))
        elif not joined: #If they're not searching and we didn't just join, do ;resume instead
            await self.ensure_same_voice_channel(ctx)
            await ctx.invoke(self._resume)
        else:
            await ctx.send(ctx.responses['music_hello'])

    @commands.command()
    @musicchecks.has_music_perms()
    async def playtop(self, ctx, *, search:str):
        async with ctx.typing():
            info = await self.ytdl_search(search)
            try:
                source = AudioInfoTransformer(discord.FFmpegOpusAudio(info['url'], **FFMPEG_OPTIONS))
            except Exception as e:
                raise e
            else:
                song = Song(source, ctx, info)

                ctx.voice_state.song_queue.putleft_nowait(song)
                await ctx.send(ctx.responses['music_topqueued'].format(str(song)))

    @commands.command()
    @musicchecks.has_music_perms()
    async def playskip(self, ctx, *, search:str):
        await ctx.invoke(self.playtop, search=search)
        await ctx.invoke(self.skip)

    @commands.command()
    async def queue(self, ctx): #Yes I know this looks awfully similar to Rythm's 👀. What can I say, Rythm sets a good standard.
        if len(ctx.voice_state.song_queue) == 0 and not ctx.voice_state.current:
            await ctx.send(ctx.responses['music_notplaying'])
            return
        embed = discord.Embed(title=ctx.responses['music_queue'], color=discord.Color.from_rgb(233, 160, 63))
        embed.add_field(name='**__' + ctx.responses['music_nowplaying'] + '__**',
                        value=ctx.voice_state.current.get_queue_entry(),
                        inline=False)
        queue_time = ctx.voice_state.current.duration if ctx.voice_state.current.duration else 0 #Why isn't duration a variable yet? idk...
        if len(ctx.voice_state.song_queue) > 0: #if we have more than one song coming up
            display_str = ""
            for index, song in enumerate(ctx.voice_state.song_queue):
                display_str += "{0}. {1}\n\n".format(index+1, song.get_queue_entry()) #Gotta have than human friendly index
                if song.duration:
                    queue_time += song.duration
            embed.add_field(name='**__' + ctx.responses['music_upnext'] + '__**',
                        value=display_str)
        if queue_time > 0:
            embed.set_footer(text=ctx.responses['music_estimatedlength'].format(Song.parse_duration(queue_time)))
        await ctx.send(embed=embed)

    @commands.command(aliases=['nowplaying', 'playing'])
    async def np(self, ctx):
        if not ctx.voice_state.current:
            await ctx.send(ctx.responses['music_notplaying'])
            return
        await ctx.send(embed=ctx.voice_state.current.get_embed())

    @commands.command()
    @musicchecks.has_music_perms()
    async def shuffle(self, ctx):
        #Check if there is a non-empty queue
        if len(ctx.voice_state.song_queue) <= 0:
            raise EmptyQueue("Song queue must have items in it to be shuffled.")
        ctx.voice_state.song_queue.shuffle()
        await ctx.send(ctx.responses['music_shuffled'])
        
    @commands.command()
    @musicchecks.has_music_perms()
    async def clear(self, ctx):
        if len(ctx.voice_state.song_queue) <= 0:
            raise EmptyQueue("Song queue must have items in it for it to be cleared.")
        ctx.voice_state.song_queue.clear()
        await ctx.send(ctx.responses['music_cleared'])

    @commands.command()
    @checks.is_admin()
    async def djrole(self, ctx, role:discord.Role=None):
        if role:
            self.bot.datamanager.set_option(ctx.guild.id, 'dj_role', role.id)
            await ctx.send(ctx.responses['music_djroleset'].format(role))
        else:
            if ctx.options['dj_role'].data == "0": #The server hasn't set a DJ role.
                await ctx.send(ctx.responses['music_nodjrole'])
                return
            else:
                dj_role = ctx.guild.get_role(int(ctx.options['dj_role'].data))
                if not dj_role:
                    await ctx.send(ctx.responses['music_ghostdjrole'])
                    return
                await ctx.send(ctx.responses['music_djrole'].format(dj_role))

    @commands.command(aliases=['removedjrole', 'nodjrole'])
    @checks.is_admin()
    async def unsetdjrole(self, ctx):
        if ctx.options['dj_role'].data == "0":
            await ctx.send(ctx.responses['music_nodjrole'])
            return
        self.bot.datamanager.remove_option(ctx.guild.id, 'dj_role')
        await ctx.send(ctx.responses['music_unsetdjrole'])

    """
    Joining: Must be in any channel
    Leaving: No requirements
    Pausing: Must be in same channel
    Playing (Queuing): Must be in same channel
    Resuming: Must be in same channel
    Summoning (will be combined with ;join): Must be in any channel
    Shuffling: Must be in same channel
    Skipping: Must be in same channel
    """

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_user_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise UserNotInVoice('You must be in a voice channel to use that command.')

    @skip.before_invoke
    @_pause.before_invoke
    @_resume.before_invoke
    @shuffle.before_invoke
    @removedupes.before_invoke
    @playtop.before_invoke
    @playskip.before_invoke
    @leavecleanup.before_invoke
    async def ensure_same_voice_channel(self, ctx: commands.Context):
        if ctx.voice_client is not None and ctx.author.voice is not None:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise NotInSameVoiceChannel('You must be in the same voice channel as the bot to use this command.')
            return True
        #If neither of them are in a channel
        raise NotInSameVoiceChannel('You must be in the same voice channel as the bot to use this command.')

    async def close_all(self):
        for voice in self.voice_states.values():
            await voice.close()
        self.voice_states = {}

def setup(bot):
    global mcog
    mcog = MusicCog(bot)
    bot.add_cog(mcog)

def teardown(bot):
    global mcog
    task = bot.loop.create_task(mcog.close_all())
    bot.loop.run_until_complete(task)