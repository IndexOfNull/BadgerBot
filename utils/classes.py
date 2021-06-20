from discord.ext.commands.help import DefaultHelpCommand
from discord.ext.commands.context import Context

class CustomHelpCommand(DefaultHelpCommand): #subclass the help formatter

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_ending_note(self):
        return ""

class CustomContext(Context):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ignore_errors = False #A flag to be set when errors should be ignored

    ####Options Code####
    def injectcustom(self):
        if not self.guild:
            self.options = self.bot.datamanager.get_options("dm")
        else:
            self.options = self.bot.datamanager.get_options(self.guild.id)
        self.basic_options = {name: data for name, data in self.options.items()} #Converts {'optname': row} to {'optname': value}; this does not give direct access to the row object
        #Wow this is a mess
        if self.options['lang'].data in self.bot.responses:
            if self.options['responses'].data in self.bot.responses[self.options['lang'].data]:
                self.responses = self.bot.responses[self.options['lang'].data][self.options['responses'].data]
                return
        #Default if for some reason the selected language or response set doesn't exist anymore
        self.responses = self.bot.responses['en']['default']

    def get_response(self, key, *f, **f_kwargs):
        path_keys = key.split(".")
        current_location = self.responses
        for _ in range(len(path_keys)):
            key = path_keys.pop(0)
            current_location = current_location[key]
        if f or f_kwargs:
            current_location = current_location.format(*f, **f_kwargs)
        return current_location

    async def send_response(self, key, *f, **f_kwargs):
        response = self.get_response(key, *f, **f_kwargs)
        await self.send(response)