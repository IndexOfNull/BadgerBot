from discord.ext.commands.help import DefaultHelpCommand
from discord.ext.commands.context import Context
import discord
import discord.ext

class CustomHelpCommand(DefaultHelpCommand): #subclass the help formatter

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_ending_note(self):
        return ""

class CustomContext(Context):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._blacklist = {} #Too bad we can't check if the command is valid here, so we'll just have to force people to use is_blacklisted
        self._blacklist_ids = {}
        self._global_blacklist = {}
        self._global_blacklist_ids = {}
        """
            You may be wondering: why do we bother seperating _blacklist and _global_blacklist? That is mainly
            to make it easier to figure out what blacklists to show to servers when running commands apart of
            the blacklist command group (@commands.group())
        """

    ####Blacklist code####
    def is_blacklisted(self, obj):
        if isinstance(obj, discord.Guild): #handle guild
            if obj.id in self._blacklist_ids['servers'] or obj.id in self._global_blacklist_ids['servers']: #Check if its in the server spefic blacklist or in the global blacklist
                return True
        if isinstance(obj, discord.TextChannel): #handle text channel
            if obj.id in self._blacklist_ids['channels'] or obj.id in self._global_blacklist_ids['channels']:
                return True
        if isinstance(obj, discord.ext.commands.Command): #handle command
            if obj.name in self._blacklist_ids['commands'] or obj.name in self._global_blacklist_ids['commands']:
                return True
        if isinstance(obj, discord.User) or isinstance(obj, discord.Member): #handle user
            if obj.id in self._blacklist_ids['users'] or obj.id in self._global_blacklist_ids['users']:
                return True
        if isinstance(obj, discord.ext.commands.Context): #All of the above
            results = []
            results.append(self.is_blacklisted(self.guild))
            results.append(self.is_blacklisted(self.channel))
            results.append(self.is_blacklisted(self.command))
            results.append(self.is_blacklisted(self.author))
            return True in results

    def populate_blacklists(self):
            self._blacklist = self.bot.datamanager.get_blacklists(self.guild.id) #Get the blacklists
            #Convert all the row objects into ids
            blacklist_temp = {key: [] for key in self._blacklist.keys()} #Clone only the keys
            global_temp_ids = {key: [] for key in self._blacklist.keys()}
            global_temp = {key: [] for key in self._blacklist.keys()}
            for cat in self._blacklist.keys():
                r = []
                g = []
                gr = []
                for row in self._blacklist[cat]:
                    if row.server_id != 0: #Keep server specific blacklists and global blacklists seperate
                        if row.target_id: r.append(row.target_id)
                        if row.target_name: r.append(row.target_name)
                    else:
                        if row.target_id: g.append(row.target_id)
                        if row.target_name: g.append(row.target_name)
                        gr.append(row)
                        self._blacklist[cat].remove(row) #Remove the row from _blacklist if its global
                global_temp[cat] = gr
                blacklist_temp[cat] = r
                global_temp_ids[cat] = g
            self._blacklist_ids = blacklist_temp
            self._global_blacklist_ids = global_temp_ids
            self._global_blacklist = global_temp
            return self._blacklist_ids

    @property
    def blacklisted(self): #Is the whole context blacklisted?
        if self._blacklist == {}: #Ensure that the blacklist table is populated
            self.populate_blacklists()
        return self.is_blacklisted(self)

    @property
    def blacklist(self): #Return self._blacklist, populating it if necessary 
        if self._blacklist == {}: #Ensure that the blacklist table is populated
            self.populate_blacklists()
        return self._blacklist

    @property
    def blacklist_ids(self): #Return self._blacklist, populating it if necessary 
        if self._blacklist == {}: #Ensure that the blacklist table is populated
            self.populate_blacklists()
        return self._blacklist_ids

    @property
    def global_blacklist(self):
        if self._blacklist == {}: #Ensure that the blacklist table is populated
            self.populate_blacklists()
        return self._global_blacklist

    @property
    def global_blacklist_ids(self):
        if self._blacklist == {}: #Ensure that the blacklist table is populated
            self.populate_blacklists()
        return self._global_blacklist_ids

    ####Options Code####
    def injectcustom(self):
        self.options = self.bot.datamanager.get_options(self.guild.id)
        self.basic_options = {name: data for name, data in self.options.items()} #Converts {'optname': row} to {'optname': value}; this does not give direct access to the row object
        #Wow this is a mess
        if self.options['lang'].data in self.bot.responses:
            if self.options['responses'].data in self.bot.responses[self.options['lang'].data]:
                self.responses = self.bot.responses[self.options['lang'].data][self.options['responses'].data]
                return
        #Default if for some reason the selected language or response set doesn't exist anymore
        self.responses = self.bot.responses['en']['default']
