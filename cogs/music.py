#This module makes use of the PyNaCl library, you may remove PyNaCl if you decide not to enable this. This module will also likely depend on libopus, so have that installed.
#Also huge thanks to this gist: https://gist.github.com/vbe0201/ade9b80f2d3b64643d854938d40a0a2d
from discord.ext import commands
import asyncio

#Maybe implement a song class to hold info about a song (like source, who requested it, other metadata, etc)

#Also perhaps a SongQueue class extended from asyncio.Queue?

class VoiceError(Exception): pass

class VoiceState(): #Responsible for managing all audio activity in a guild

    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self._bot = ctx.bot
        self.playing = None
        self.voice = None #This will get set later by the actual music cog
        self.next_event = asyncio.Event() #Event to tell audio coroutine when it needs to move on to the next song
        self.audio_player = self._bot.loop.create_task(self.audio_player_task())

    async def audio_player_task(self):
        while True:
            self.next_event.clear() #Reset the next flag
            #Disconnect code here
            #Playing code here
            await self.next_event.wait() #Wait for the next event to be triggered

    def next_song(self, error=None): #callback for when the current playing song finishes
        if error:
            raise VoiceError(str(error))
        self.next_event.set()

class MusicCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, ctx: commands.Context):
        state = self.voice_states.get(ctx.guild.id)
        if not state:
            state = VoiceState(ctx)
            self.voice_states[ctx.guild.id] = state
        return state

    async def cog_before_invoke(self, ctx: commands.Context): #Get ourselves a music context! (Only accessable throughout this cog)
        ctx.voice_state = self.get_voice_state(ctx)

    @commands.command(name="join", invoke_without_subcommand=True)
    async def _join(self, ctx: commands.Context):
        channel = ctx.author.voice.channel
        if ctx.voice_state.voice: #If we have an existing connection, move it!
            await ctx.voice_state.voice.move_to(channel)
            return
        ctx.voice_state.voice = await channel.connect()

    @commands.command()
    async def play(self, ctx):
        if not ctx.voice_state.voice:
            await ctx.invoke(self._join)
        

def setup(bot):
    bot.add_cog(MusicCog(bot))