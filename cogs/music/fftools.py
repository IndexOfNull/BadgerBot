import subprocess
import json
import re

"""
Tools for FFMpeg

NOTE: These *may* work with AVConv, but it isn't tested and I highly advise against it
"""

def get_codec_info(source, executable="ffmpeg"):
    exe = executable[:2] + 'probe' if executable in ('ffmpeg', 'avconv') else executable
    args = [exe, '-v', 'quiet', '-print_format', 'json', '-show_streams', '-select_streams', 'a:0', source]
    output = subprocess.check_output(args, timeout=20)
    data = None

    if output:
        data = json.loads(output)

    return data

def get_supported_formats(executable="ffmpeg"):
    exe = executable[:2] + 'probe' if executable in ('ffmpeg', 'avconv') else executable
    args = [exe, '-formats', '-loglevel', 'panic', '-hide_banner']
    output = subprocess.check_output(args, timeout=20)
    if output:
        info = {}
        output = output.decode().split("--") #Get everything after the tiny header
        output = output[1].splitlines()[1:] #Get each line, and trim off the first element, as it is a newline and empty
        for format in output:
            support = (format[1] == "D", format[2] == "E") #Demuxing, muxing
            pattern = re.compile("[^ ]*")
            name = pattern.match(format[4:]) #Trim off the start crap and find out the name
            if not name.group(0):
                raise KeyError("Something went horribly wrong while extracting the codec name!")
            info[name.group(0)] = support
        return info
    raise Exception("FFMpeg/AVconv did not properly return an output")