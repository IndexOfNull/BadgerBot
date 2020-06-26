import discord
from discord.ext import commands

def has_music_perms(): #Passes if the user is the only one with the bot, the bot is alone, if they have a DJ role, or if DJ roles are disabled
    def predicate(ctx):
        dj_role_enabled = True #This should be pulled from server options once I figure that part out
        if not dj_role_enabled: #Don't even bother with these other checks if they're supposed to have perms anyway
            return True
        #If the user is the only one in the channel with the bot, give them access regardless of roles
        if ctx.voice_client:
            bot_channel = ctx.voice_client.channel
            if len(bot_channel.members) == 1: #If the bot is the only one in the channel
                return True
            if ctx.author.voice:
                if bot_channel == ctx.author.voice.channel and len(bot_channel.members) <= 2: #If the invoker is in the same channel as the bot and they are the only one in it besides the bot
                    return True
        elif ctx.author.voice: #If the bot isn't in a channel, but the user is.
            if len(ctx.author.voice.channel.members) == 1: #Allow if they are the only one in the channel
                return True
        else:
            return True #Allow if the bot or the user isn't in a channel
        if dj_role_enabled: #Otherwise, check if they have the proper roles/perms
            if not isinstance(ctx.channel, discord.abc.GuildChannel):
                raise NoPrivateMessage()
            roles = set(('DJ', 'Music'))
            if len(roles.intersection(set([r.name for r in ctx.author.roles]))) > 0:
                return True
            else:
                raise commands.MissingAnyRole(roles)
            
        return True #Give access if all other restrictions pass
    return commands.check(predicate)