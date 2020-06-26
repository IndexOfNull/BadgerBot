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
from io import BytesIO

from cogs.music import fftools

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
        self._ms_read += 20 #20 is the default discord.py FRAME_LENGTH (see Encoder in discord/opus.py)
        return self.original.read()

class SongQueue(asyncio.Queue):
    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]

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
    def format_timebar(current=None, duration=None, *, length=25, dash='-', dot='🔵', unknown="Unknown"):
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
            s += "(Unknown Duration)"
        if self.requester:
            s += " | Requested by: " + self.requester.mention
        return s

    def get_embed(self): #Add localization string for this later
        embed = discord.Embed(description='```yaml\n{0}\n```'.format(self.title),
                               color=discord.Color.from_rgb(233, 160, 63))

        if self.requester:
            embed.set_author(name='Now playing', icon_url=self.requester.avatar_url_as(size=128))
        else:
            embed.title = 'Now playing'

        if isinstance(self.source, AudioInfoTransformer): #If we even have access to the current head
            bar = '`' + self.parse_duration(self.source.head/1000) + '` ' #Get the number of seconds passed
            if not self.duration:
                bar += '/ `Unknown`'
            else:
                bar += self.format_timebar(self.source.head/1000, self.duration) + ' `' + self.parse_duration(self.duration) + '`'
            bar += ' '
            #bar += 'Unknown' if not self.duration else self.parse_duration(self.duration) #Get the duration if possible, otherwise just say its unkown
            embed.add_field(name='Timebar', value=bar)

        if self.uploader and self.uploader_url:
            embed.add_field(name='Uploader', value='[{0}]({1})'.format(self.uploader, self.uploader_url))
        elif self.uploader or self.uploader_url:
            embed.add_field(name='Uploader', value=(self.uploader + '\n' if self.uploader else '') + ('[' + self.uploader_url + ']' if self.uploader_url else ''), inline=False)
        
        if self.url:
            embed.add_field(name='Source', value='[Click]({0})'.format(self.url))

        embed.add_field(name='Requested by', value=self.requester.mention)
        if self.thumbnail:
            embed.set_thumbnail(url=self.thumbnail)
        if self.extractor:
            if not self.extractor == 'generic':
                embed.set_footer(text='From ' + self.extractor.capitalize())
            else:
                embed.set_footer(text='From an MP3 file, probably...') 

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

class VoiceError(Exception): pass
class YTDLError(Exception): pass

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
            return member_count // 3 #One third of the users, leaning towards the smaller side

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
            raise VoiceError(str(error))
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
            self.after_handler()
        else:
            self.voice.resume() #Only resume if we are actually resuming the same track, otherwise it will create a weird sounding blip.
        
    def pause(self): #Pause the current song and queue
        self.voice.pause()
        self._paused = True

    def skip(self):
        self.voice.stop() #This stops the current song, do not be confused. This also calls the "after" callback set in self.voice.play()

    async def close(self, timeout=False): #Stop audio and disconnect
        self.song_queue.clear()
        if self.voice:
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
        recommended_demuxers = ('h264', 'h265', 'mp3', 'aac', 'dash', 'webm_dash_manifest', 'matroska,webm')
        missing_demuxers = []
        demuxers = fftools.get_supported_formats()
        for demuxer in recommended_demuxers:
            if demuxer in demuxers:
                if not demuxers[demuxer][0]:
                    missing_demuxers.append(demuxer)
        if missing_demuxers:
            j = ";".join(missing_demuxers)
            print("You are missing support to demux the following formats, some sources may not work properly: " + j)

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
        
        return info

    def get_voice_state(self, ctx: commands.Context): #Typing in Python? What!
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(ctx)
            self.voice_states[ctx.guild.id] = state
        return state

    async def cog_before_invoke(self, ctx: commands.Context): #Get ourselves a music context! (Only accessable throughout this cog)
        ctx.voice_state = self.get_voice_state(ctx)

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
            if not after.channel == state.voice.channel:
                state.skips.discard(member.id) #Discard the users vote if they are moving out of the bots channel

    @commands.command(name="join", invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        channel = ctx.author.voice.channel
        if ctx.voice_state.voice: #If we have an existing connection, move it!
            await ctx.voice_state.voice.move_to(channel)
            return
        ctx.voice_state.voice = await channel.connect()

    @commands.command()
    async def skip(self, ctx):
        #Check if they have already voted

        #THESE CHECKS SHOULD MAKE THERE WAY INTO A before_invoke DECORATED FUNCTION!11!1
        """if not ctx.voice_state.is_playing:
            await ctx.send("Bot must be playing in order to skip.") #Add localization string for this later
            return"""
        if ctx.voice_state.is_empty:
            await ctx.send("Empty queue") #Add localization string for this later
            return
        if ctx.author.id in ctx.voice_state.skips:
            await ctx.send("Already voted!") #Add localization string for this later
            return

        ctx.voice_state.skips.add(ctx.author.id)
        if len(ctx.voice_state.skips) >= ctx.voice_state.skips_required:
            ctx.voice_state.skip()
            await ctx.send("Skipped!") #Add localization string for this later
            return
        await ctx.send("Added skip vote!") #Add localization string for this later

    @commands.command(name="pause", aliases=["stop"], invoke_without_subcommand=True)
    async def _pause(self, ctx: commands.Context):
        if ctx.voice_state.is_playing:
            ctx.voice_state.pause()
            await ctx.send("Paused") #Add localization string for this later
            return
        await ctx.send("Not playing") #Add localization string for this later
    
    @commands.command(name="resume", invoke_without_subcommand=True)
    async def _resume(self, ctx: commands.Context):
        if ctx.voice_state.is_playing:
            await ctx.send("Already playing") #Add localization string for this later
            return
        if ctx.voice_state.is_empty:
            await ctx.send("Empty queue") #Add localization string for this later
            return
        ctx.voice_state.resume()
        await ctx.send("Resumed") #Add localization string for this later
        return
        
    @commands.command(name="leave", invoke_without_subcommand=True)
    async def _leave(self, ctx: commands.Context):
        if not ctx.voice_state.voice: #Check if we are connected, if not, throw an error
            raise VoiceError("Cannot leave unless connected to a channel.")
        await self.unregister_voice_state(ctx, auto_close=True)

    @commands.command(name="play")
    async def _play(self, ctx, *, search:str=None):
        if not ctx.voice_state.voice: #Join if we aren't already connected
            await ctx.invoke(self._join)
        if search:
            async with ctx.typing():
                info = await self.ytdl_search(search)
                try:
                    #source = discord.FFmpegOpusAudio(info['url']) #FFmpegOpusAudio seems faster (going by ear), but incapable of modulating volume on the fly
                    #fftools.get_codec_info(info['url'])
                    #source = await CustomOpusSource.from_probe(info['url'])
                    source = AudioInfoTransformer(discord.FFmpegOpusAudio(info['url'], **FFMPEG_OPTIONS))
                except Exception as e:
                    raise e
                else:
                    song = Song(source, ctx, info)

                    await ctx.voice_state.song_queue.put(song)
                    await ctx.send('```diff\n+ Queued: {}\n```'.format(str(song)))
        else:
            await ctx.invoke(self._resume) #If they're not searching, do ;resume instead

    @commands.command()
    async def test(self, ctx):
        await ctx.invoke(self._play, search="tabloid jargon")
        await ctx.invoke(self._play, search="https://soundcloud.com/capsadmin/oh_z")
        await ctx.invoke(self._play, search="purpdaniel")

    @commands.command()
    async def queue(self, ctx): #Yes I know this looks awfully similar to Rythm's 👀. What can I say, Rythm sets a good standard.
        embed = discord.Embed(title='🎵 Queue 🎵', color=discord.Color.from_rgb(233, 160, 63)) #Add localization string for this later
        embed.add_field(name='**__Now Playing__**', #Add localization string for this later
                        value=ctx.voice_state.current.get_queue_entry(),
                        inline=False)
        queue_time = ctx.voice_state.current.duration if ctx.voice_state.current.duration else 0 #Why isn't duration a variable yet? idk...
        if len(ctx.voice_state.song_queue) > 0: #if we have more than one song coming up
            display_str = ""
            for index, song in enumerate(ctx.voice_state.song_queue):
                display_str += "{0}. {1}\n\n".format(index+1, song.get_queue_entry()) #Gotta have than human friendly index
                if song.duration:
                    queue_time += song.duration
            embed.add_field(name='**__Up Next__**', #Add localization string for this later
                        value=display_str)
        if queue_time > 0:
            embed.set_footer(text='Estimated Length: {0} (sources of unknown length are not included)'.format(Song.parse_duration(queue_time)))
        await ctx.send(embed=embed)

    @commands.command()
    async def np(self, ctx):
        await ctx.send(embed=ctx.voice_state.current.get_embed())

    @commands.command(name='summon')
    #@commands.has_permissions(move_members=True)
    async def _summon(self, ctx: commands.Context, *, channel: discord.VoiceChannel = None):
        """Summons the bot to a voice channel.
        If no channel was specified, it joins your channel.
        """

        if not channel and not ctx.author.voice:
            raise VoiceError('You are neither connected to a voice channel nor specified a channel to join.')

        destination = channel or ctx.author.voice.channel
        if ctx.voice_state.voice:
            await ctx.voice_state.voice.move_to(destination)
            return

        ctx.voice_state.voice = await destination.connect()

    @commands.command()
    async def shuffle(self, ctx):
        #Check if there is a non-empty queue
        if len(ctx.voice_state.song_queue) <= 0:
            raise VoiceError("Song queue must have items in it to be shuffled.")
        ctx.voice_state.song_queue.shuffle()
        
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
    @_summon.before_invoke
    async def ensure_user_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise VoiceError('You must be in a voice channel to use that command.')

    @skip.before_invoke
    @_pause.before_invoke
    @_resume.before_invoke
    @_play.before_invoke
    @shuffle.before_invoke
    async def ensure_same_voice_channel(self, ctx: commands.Context):
        if ctx.voice_client and ctx.author.voice:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise VoiceError('You must be in the same voice channel as the bot to use this command.')
            return
        #If neither of them are in a channel
        raise VoiceError('You must be in the same voice channel as the bot to use this command.')
    
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