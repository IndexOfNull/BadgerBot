



class RenderManager():

    def __init__(self, db, **kwargs):
        self.themes = []
        self.widgets = []
        self.events = {}
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

    def broadcast(self, event, data): #Broadcast something to all widgets.
        for widget in self.widgets:
            widget.on_event(event, data)

    def register_event(self, event, func):
        if event in self.events:
            raise Exception("You cannot register two events to the same event name")
        self.events[event] = func

    def fire_event(self, e, *args, **kwargs):
        return self.events[e](*args, **kwargs)

    def get_widget(self, name):
        for widget in self.widgets:
            if name == widget.name or name == widget.__class__.__name__:
                return widget

