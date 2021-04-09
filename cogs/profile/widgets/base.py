class WidgetBase():

    def __init__(self, db, manager, **kwargs):
        self.db = db
        self.render_manager = manager
        self.build_tables = kwargs.pop("create_tables", False)
        self.embed_only = False
        self.name = kwargs.pop("name", None)

    def render_image(self, theme): #Render for the profile screen
        raise NotImplementedError()

    def render_leaderboard(self, theme): #Render a text leaderboard
        raise NotImplementedError()

    def on_event(self, event, data): #Handle custom messaging implementations
        pass

    def handle_embed(self, ctx, user, embed):
        pass