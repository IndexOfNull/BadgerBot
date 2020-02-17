
# Additional Information

Here you can find a bit of additional documentation about how some components of the bot work. This is not meant to be a complete documentation of everything, but should make certain things feel less "magical".

  

## The Render Manager, Themes, and Widgets

The idea behind the profile and widget system is that there are 3 components:

  

1. A render manager that registers widgets and themes

2. A theme that registers widgets

3. A widget that actually handles the dirty work

  

The idea behind a render manager is that it oversees everything necessary to get a nice profile. It is the highest level of interfacing with everything. Keep reading to see how some features are utilized.

  

### Communication: Broadcasts

A broadcast is a message sent (from the render manager) to every widget containing an event name (so widgets can listen for certain broadcasts) and a payload. Widgets can currently receive information this way by implementing `on_event(event, data)`. Here's a rough example of how this might work:

```python

#Inside the widget class

def  on_event(self, event, payload)

print("Event!", event, payload)

  

#Somewhere else that has access to the render manager

render_manager.broadcast("testevent", "testpayload")

```

  

### Communication: Events

An event is like a broadcast, but only one widget will actually receive it. This allows us to target exactly one widget. The benefit to this is that we can actually get a return value, which may prove useful for more "intelligent" tasks. They can be implemented like this:

```python

#Inside the widget class

def  __init__(self, *args, **kwargs):

super().__init__(*args, **kwargs) #This will assign self.render_manager

#init code...

self.render_manager.register_event("testevent", self.handler)

  

def  handler(self, *args, **kwargs): #Your handler may receive different args

print("We got an event!", args, kwargs)

return  True

  

#Elsewhere

result = render_manager.fire_event("testevent", "1", foo=2)

#result -> True

```

### Display: Embeds

The original plan during development was to render out full images. But I ended up just using discord embeds instead, which seem to work well. At the time of writing themes and `render_image()` are basically unused. So you may find remnants of that code.

  

Anyway, when the render manager is asked for a profile with `get_embed(ctx, user, embed)` (you pass it an already initialized `discord.Embed`) it goes through all the widgets and gives it the embed to manipulate. This is possible because many features of the `discord.Embed` class are modified in-place, so we can just pass the same class in a simple `for` loop. The plus side to this is that widgets can also handle how they display things in a fairly arbitrary and modular manner.

  

Widgets can implement an embed handler function like this:

```python

def  handle_embed(ctx, user, embed):

t = user.joined_at

if t: #user.joined_at can sometimes return None

converted_time = t.strftime('%Y-%m-%d %H:%M:%S') + " UTC"

embed.add_field(name="Date Joined", value=converted_time)

```

That would add a "Date Joined" field to the embed. As mentioned above, we don't have to return anything because modification is done in-place.

### Miscellaneous

A few other things exist about the render manager that don't demand a full expanation. They can be found here.

  

Getting a widget by name:

```python

widget = render_manager.get_widget("BadgeWidget") #by class name or by Widget.name

```

  

## The Built-in Webserver

The bot also ships with a webserver baked into it. This allows (albeit basic) communications from other services with widgets. It can be thought of as a REST API. The webserver can be used to broadcast and fire widget events.

### Authenticating
Web requests also need to send the secret contained in the `config.json` file for requests to be accepted. You can pass the secret in two ways:
```
#Via headers
Authorization: SECRET

#Via params
/broadcast?secret=SECRET
```
### Broadcasting

```POST /broadcast?event=event&payload=payload```

  

The `event` and `payload` params are both required and an error will be returned if either of them are not included. See below for how responses will be formatted.

### Firing Events

```POST /event?event=event&payload=payload```

  

This is functionally the same as broadcasting. But your response will also include a return value. Successful responses may look like this:

  

```json

{"status": "good", "result": "some return value"}

```

### Responses

Requests that error will respond with a HTTP status code corresponding to the type of error along with a JSON encoded body with more information. They may look like this:

```json

{"status": "error", "error": "The specified event does not exist."}

```

  

Requests that are successful give a short and sweet response:

```json

{"status": "good"}

```

  

## Data!

The bot also handles a decent amount of server specific information. Without going into too much detail, a class (`DataManager`) will register a bunch of different "options" with default values. It can then fetch a server's options while filling in any missing ones with their defaults. This allows us to pretty conveniently store info on a per-server basis.

  

That's not anything particularly special in and of itself, but the DataManager also does something else very important: command prefixes. Prefixes are handled a bit differently, and for good reason. An inherent problem with our current database implementation is that it is blocking, so it isn't really "up to snuff" for asyncio. This isn't really a big issue just as long as database calls are kept to a minimum. That is, everything should be fine as long as we don't call on the database every time we get a message, and that's exactly what we do. ***The `DataManager` class also keeps a local table of prefixes in memory to keep database load light.***