
def widget_event(event):#cl, func, event):
    def real_decorator(func):
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
        return wrapper
    return real_decorator

class WidgetBase():

    def __init__(self, db, manager, **kwargs):
        self.db = db
        self.render_manager = manager
        self.build_tables = kwargs.pop("create_tables", False)
        self.embed_only = False

    def render_image(self, theme): #Render for the profile screen
        raise NotImplementedError()

    def render_leaderboard(self, theme): #Render a text leaderboard
        raise NotImplementedError()

    def on_event(self, event, data): #Handle custom messaging implementations
        pass

    def handle_embed(self, embed):
        pass

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

class RenderManager():

    def __init__(self, db, **kwargs):
        self.themes = []
        self.widgets = []
        self.db = db
        self.build_tables = kwargs.pop("create_tables", False) #Should we build tables based on the schema?
        
    def register_widget(self, widget):
        w = widget(self.db, self, create_tables=self.build_tables)
        self.widgets.append(w)
        return w

    def register_theme(self, theme):
        t = theme(self)
        self.themes.append(t)
        return t

    def broadcast_event(self, event, data):
        for widget in self.widgets:
            widget.on_event(event, data)


