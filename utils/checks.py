from discord.ext import commands

#Quite a bit of this is more-or-less copied from the discord library. Thanks Rapptz!

class MissingAnyPermissions(commands.CheckFailure): 

    def __init__(self, missing_perms, *args):
        self.missing_perms = missing_perms

        missing = [perm.replace('_', ' ').replace('guild', 'server').title() for perm in missing_perms]

        if len(missing) > 2:
            fmt = '{}, or {}'.format(", ".join(missing[:-1]), missing[-1])
        else:
            fmt = ' or '.join(missing)
        message = 'You need {} permission(s) to run this command.'.format(fmt)
        super().__init__(message, *args)

class MissingAdmin(MissingAnyPermissions): pass
class MissingModerator(MissingAnyPermissions): pass

def has_any_permissions(**perms): #This is basically just commands.has_permissions with the logic flipped around
    def predicate(ctx):
        ch = ctx.channel
        permissions = ch.permissions_for(ctx.author)

        not_missing = [perm for perm, value in perms.items() if getattr(permissions, perm, None) == value]
        if not_missing:
            return True

        raise MissingAnyPermissions(perms.keys())
    return commands.check(predicate)

#honestly, I could just put the decorators for these in front
#of all the commands requiring them, but this is easier.
admin_perms = {"administrator": True, "manage_guild": True, "ban_members": True}
mod_perms = {"manage_messages": True, "kick_members": True}
#could it be possible to be an admin and not a mod? That would probably never happen with anyone who knows how to use discord...

#These are the wrappers for the decorators. We can use these to infer if somewhat has admin status in a #general sense.
def is_admin():
    try:
        return has_any_permissions(**admin_perms)
    except MissingAnyPermissions:
        raise MissingAdmin

def is_mod():
    try:
        return has_any_permissions(**mod_perms) or has_any_permissions(**admin_perms)
    except MissingAnyPermissions:
        raise MissingModerator

