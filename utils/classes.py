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
        self.options = self.bot.datamanager.get_options(self.guild.id, basic=True)
        #Wow this is a mess
        if self.options['lang'] in self.bot.responses:
            if self.options['responses'] in self.bot.responses[self.options['lang']]:
                self.responses = self.bot.responses[self.options['lang']][self.options['responses']]
                return
        #Default if for some reason the selected language or response set doesn't exist anymore
        self.responses = self.bot.responses['en']['default']
                