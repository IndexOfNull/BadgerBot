#This module makes use of the PyNaCl library, you may remove PyNaCl if you decide not to enable this. This module will also likely depend on libopus, so have that installed.
#Also huge thanks to this gist: https://gist.github.com/vbe0201/ade9b80f2d3b64643d854938d40a0a2d
import discord
from discord.ext import commands
import asyncio
from async_timeout import timeout
import itertools
import random

#Maybe implement a song class to hold info about a song (like source, who requested it, other metadata, etc)

mcog = None

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

    def __init__(self, source, ctx:commands.Context=None):
        self.source = source
        self.ctx = None
        self.requester = None
        if ctx:
            self.ctx = ctx
            self.requester = ctx.author

    def __repr__(self):
        return str(self.source)

class VoiceError(Exception): pass

class VoiceState(): #Responsible for managing all audio activity in a guild

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self._bot = ctx.bot

        self.current = None
        self.voice = None #This will get set later by the actual music cog
        self.next_event = asyncio.Event() #Event to tell audio coroutine when it needs to move on to the next song
        self.audio_player = self._bot.loop.create_task(self.audio_player_task())
        self.song_queue = SongQueue()

        self.loop = False #Loop the queue? This will be further implemented later
        self.skips = set()

    @property
    def is_playing(self): #Check if we are playing anything
        if self.voice: #Have to do this to be save that we have a VoiceClient instance.
            return self.current and self.voice.is_playing() #if there is a voice instance, check if it is playing anything
        return False

    @property
    def is_empty(self): #Check if the queue and playing are empty (awaiting a song)
        return not self.is_playing and ( len(self.song_queue) == 0 and not self.current)

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

    def __del__(self):
        self.audio_player.cancel() #Make sure we stop the audio player task when we clean up

    async def audio_player_task(self):
        while True:
            self.next_event.clear() #Reset the next flag

            #Make sure that we are still playing stuff, otherwise disconnect after some time
            if not self.loop:
                try:
                    async with timeout(180):
                        self.current = await self.song_queue.get() #Get a song from the queue with a timeout of 180
                except asyncio.TimeoutError:
                    self._bot.loop.create_task(self.close())
                    return
                
            #Play the stuff
            self.voice.play(self.current.source, after=self.next_song)
            await self.next_event.wait() #Wait for the next event to be triggered

    def next_song(self, error=None): #callback for when the current playing song finishes
        if error:
            raise VoiceError(str(error))
        self.current = None #Unset the current song (this will be set back in audio_player_task if there is another queued item)
        self.skips.clear() #Clear all votes to skip
        self.next_event.set()

    def skip(self):
        self.voice.stop() #This stops the current song, do not be confused. This also calls the "after" callback set in self.voice.play()

    async def close(self): #Stop audio and disconnect
        self.song_queue.clear()
        if self.voice:
            self.voice.stop()
            await self.voice.disconnect() #Close our connection
            self.voice = None #Destroy our connection

class MusicCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context): #Typing in Python? What!
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(ctx)
            self.voice_states[ctx.guild.id] = state
        return state

    async def cog_before_invoke(self, ctx: commands.Context): #Get ourselves a music context! (Only accessable throughout this cog)
        ctx.voice_state = self.get_voice_state(ctx)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after): #Removes the users vote and recomputes the number of needed votes 
        if after.channel == before.channel: #We only want to detect when a member moves or leaves, so we can ignore all other updates
            return
        state = self.voice_states.get(member.guild.id)
        if not state:
            return #Do nothing if there is no voice state for the guild
        state.skips.discard(member.id) #Discard the users vote

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
        if not ctx.voice_state.is_playing:
            await ctx.send("Bot must be playing in order to skip.") #Add localization string for this later
            return
        if ctx.author.id in ctx.voice_state.skips:
            await ctx.send("Already voted!") #Add localization string for this later
            return

        ctx.voice_state.skips.add(ctx.author.id)
        if len(ctx.voice_state.skips) >= ctx.voice_state.skips_required:
            ctx.voice_state.skip()
            await ctx.send("Skipped!") #Add localization string for this later
        await ctx.send("Added skip vote!") #Add localization string for this later

    """@commands.command()
    async def queue(self, ctx: commands.Context):
        if len(ctx.voice_state.queue)"""

    @commands.command(name="pause", aliases=["stop"], invoke_without_subcommand=True)
    async def _pause(self, ctx: commands.Context):
        if ctx.voice_state.is_playing:
            ctx.voice_state.voice.pause()
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
        ctx.voice_state.voice.resume()
        await ctx.send("Resumed") #Add localization string for this later
        return
        
    @commands.command(name="leave", invoke_without_subcommand=True)
    async def _leave(self, ctx: commands.Context):
        if not ctx.voice_state.voice: #Check if we are connected, if not, throw an error
            raise VoiceError("Cannot leave unless connected to a channel.")
        await ctx.voice_state.close()
        #del self.voice_states[ctx.guild.id]

    @commands.command(name="play")
    async def _play(self, ctx):
        if not ctx.voice_state.voice: #Join if we aren't already connected
            await ctx.invoke(self._join)
        async with ctx.typing():
            try:
                source = discord.FFmpegPCMAudio("resources/bruh.mp3")
            except Exception as e:
                raise e
            else:
                song = Song(source, ctx)

                await ctx.voice_state.song_queue.put(song)
                await ctx.send('Enqueued {}'.format(str(song)))

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

    """@commands.command(name="skip")
    async def _skip(self, ctx):
        if not ctx.voice_state.is_playing:
            raise VoiceError("Bot must be playing music in order to skip.")"""
        
    """ Gonna worry about all this later. Probably gonna rework it too.
    @_join.before_invoke
    @_play.before_invoke
    @_skip.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise VoiceError('You are not connected to any voice channel.')
        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise VoiceError('Bot is already in a voice channel.')
    """
    
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