class ThemeBase():

    def __init__(self, manager):
        self.render_manager = manager

    #The 3 function below will be implemented if/when images are done

    def render_foreground(self): #Render all the widgets. Probably onto a transparent canvas
        pass

    def render_background(self): #Render the background
        pass

    def render(self): #Create files or embeds to be sent from discord
        #composite rendered foreground and background
        pass

    def get_embed(self, ctx, user, embed):
        pass