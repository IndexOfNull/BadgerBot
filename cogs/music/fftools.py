import subprocess
import json

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