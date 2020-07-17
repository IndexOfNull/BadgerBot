import discord
from discord.ext import commands

#Passes if the user has the DJ role (if set), otherwise checks if they (or the bot) are alone with no other users.
def has_music_perms():
    def predicate(ctx):
        dj_role_id = int(ctx.options['dj_role'].data) #Will be zero if unset
        if not dj_role_id:
            return True #Allow if there is no DJ role set

        dj_role = ctx.guild.get_role(dj_role_id)
        if dj_role: #If the role exists
            if discord.utils.get(ctx.author.roles, id=dj_role_id) is not None: #If the author has the role
                return True  

        if ctx.voice_client: 
            bot_channel = ctx.voice_client.channel
            if ctx.author.voice: #If the author is in a voice channel...
                if ctx.author.voice.channel == bot_channel and len(bot_channel.members) <= 2: #and its the same as the bot and there's two or less members
                    return True
                else:
                    raise commands.MissingAnyRole(("DJ"))
            elif len(bot_channel.members) == 1: #If the bot is the only one in the channel
                return True
        elif ctx.author.voice: #implied 'and not ctx.voice_client' due to above condition
            if len(ctx.author.voice.channel.members) == 1:
                return True

        raise commands.MissingAnyRole(("DJ"))
    return commands.check(predicate)