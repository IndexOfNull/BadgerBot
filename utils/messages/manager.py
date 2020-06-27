"""

This file serves as a parser for the responses.json file. The file is structured as followed.

{
    "en": { #This is the language, and it includes the master set since it's first.
        "default": { #This is the message set. THIS IS THE MASTER SET: ALL MESSAGES MUST LIVE HERE
            ... #Messages
        }
    },
    "es": {
        "default": {} #These can have missing values, they will be filled in from the master set. Note that the message set itself will not be filled in. Different languages could have different sets.
    }
}

Message sets could be fun. Like you could make the bot super grumpy or nice.
Also this opens up the posibility for localization.

The completed table can be accessed with 'responses' like this:
messages.manager.responses
"""

import json
import os
file_path = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(file_path, "responses.json")) as f:
    responses = json.loads(f.read())

def merge(a, b, path=None): #Credit to https://stackoverflow.com/a/7205107
    "merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a

def add_response_set(s: dict):
    global responses
    responses = merge(s, responses)
    return responses

def replace_missing(master, incomplete):
    missing_keys = [key for key in master.keys() if not key in incomplete]
    for key in missing_keys:
        incomplete[key] = master[key]
    return incomplete

def build_responses(messages = None):
    if not messages: messages = responses
    master_lang = list(messages.keys())[0]
    master = messages[master_lang]['default'] #Get the first element and the default list. This will be our master list
    #Fill in the keys for each language
    for lang, responsesets in messages.items():
        for key, msgset in responsesets.items():
            if lang == master_lang and key == "default":
                continue
            completed = replace_missing(master, msgset)
            messages[lang][key] = completed
    return messages