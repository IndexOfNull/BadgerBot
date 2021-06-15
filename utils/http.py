import aiohttp
from io import BytesIO

http_session = aiohttp.ClientSession()

class InvalidMIMEType(Exception):

    def __init__(self, valid_mimes=None, *args):
        message = "File does not have a valid MIME type."
        if valid_mimes: message += " Valid MIME types are: " + ((", ").join(valid_mimes))
        super().__init__(message, *args)

async def download_media(url, *, mimes=None, errors=True, **get_kwargs): #General purpose download to a BytesIO object. Allows for MIME filtering.
    #mimes = kwargs.pop("mimes", None)
    #error = kwargs.pop("error", True) #Should we discard images without the specified mimes, or should we raise an error
    #key_val = kwargs.pop("dict", False)
    async with http_session.get(url, **get_kwargs) as response:
        if mimes: #See if we should filter for mimes and either discard or error
            if not response.content_type in mimes:
                if errors:
                    raise InvalidMIMEType(mimes)
        data = await response.read()
        b = BytesIO(data)
        b.seek(0)
        return b