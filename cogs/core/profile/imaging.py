from PIL import Image, ImageDraw, ImageFont
from utils import http
from io import BytesIO
from datetime import datetime
import re
from utils import funcs

CARD_SIZE = (1190, 700)
OPACITY = int(0.6*255)
TWEMOJI_BASE = "https://twemoji.maxcdn.com/v/latest/72x72/{codepoint}.png"


#all of this is horrible...
async def make_profile_card(ctx, user, *, badges, bg_url, spotlight):
    card_image = Image.new("RGB", CARD_SIZE, "black")
    user_color = user.color.to_rgb()

    if bg_url:
        try:
            bg_bytes = await http.download_media(bg_url, timeout=5)
            bg_img = Image.open(bg_bytes)
        except:
            bg_img = Image.open("resources/img/defaultcardbg.png") #Use a default image if fetching fails or no url is given
    else:
        bg_img = Image.open("resources/img/defaultcardbg.png")
    bg_img = bg_img.convert("RGBA")
    bg_img = aspect_resize(bg_img, CARD_SIZE)
    bg_img.putalpha(int(0.75*255)) #make it 75% transparent
    card_image.paste(bg_img, (0,0))

    draw = ImageDraw.Draw(card_image, "RGBA")
    margin = 35 #pixels

    #transparent rectangle
    bg_rect_h = 175
    bg_rect_w = CARD_SIZE[0] - margin*2
    bg_rect_pos = (margin, CARD_SIZE[1]-margin-bg_rect_h, margin+bg_rect_w-1, CARD_SIZE[1]-margin-1) #x0, y0, x1, y1
    draw.rectangle(bg_rect_pos, fill=(0, 0, 0, OPACITY)) # 60% black opacity

    num_divisions = 3
    bg_rect_division = bg_rect_w//num_divisions #Could use this to procedurally add more sections, but I'll leave this for now
    current_div = 1

    #colored part
    color_rect_h = 10
    color_rect_pos = (bg_rect_pos[0], bg_rect_pos[1]-color_rect_h, bg_rect_pos[2], bg_rect_pos[1]-1)
    draw.rectangle(color_rect_pos, fill=user_color) #reuse the position from the last rect, but offset the vertical part so this one sits above

    #divider bar
    for i in range(num_divisions-1):
        div_bar_x = bg_rect_pos[0]+bg_rect_division*(i+1)
        draw.rectangle((div_bar_x, bg_rect_pos[1]+10, div_bar_x, bg_rect_pos[3]-10), fill="white")

    #profile icon
    current_div = 1
    profile_icon_asset = user.avatar_url_as(format="png", size=512)
    profile_icon_bytes = await profile_icon_asset.read()
    profile_icon = Image.open(BytesIO(profile_icon_bytes))
    prof_side_length = bg_rect_division
    profile_icon = profile_icon.resize((prof_side_length, prof_side_length))
    profile_icon_pos = (bg_rect_pos[0], bg_rect_pos[1]+bg_rect_h-prof_side_length)
    card_image.paste(profile_icon, profile_icon_pos)

    #Spotlight
    if spotlight:
        emoji_bytes = await get_emoji_image(ctx.bot, spotlight.icon, format='png')
        spotlight_text = spotlight.name
    else:
        emoji_bytes = await get_emoji_image(ctx.bot, "🔎")
        spotlight_text = "Nothing Spotlit"
    emoji = Image.open(emoji_bytes).convert("RGBA")

    current_div = 3
    emoji_border = 14
    emoji_side_length = 128
    emoji_total_side_length = emoji_side_length + emoji_border * 2
    
    plate = Image.new("RGBA", (emoji_total_side_length, emoji_total_side_length), (user_color[0], user_color[1], user_color[2], 255))
    emoji = emoji.resize((emoji_side_length, emoji_side_length))
    plate.paste(emoji, (emoji_border, emoji_border), emoji)
    emoji_x = int(margin + (bg_rect_division*current_div - bg_rect_division/2) - emoji_total_side_length/2)
    emoji_y = int((color_rect_pos[1] + color_rect_h//2) - emoji_total_side_length/2)
    card_image.paste(plate, (emoji_x, emoji_y))
    
    #prepare spotlight text
    current_div = 3
    text_margin = 20
    spotlight_font = ImageFont.truetype("resources/fonts/DejaVuSans.ttf", size=70)
    scaled = scaled_text(spotlight_font, (bg_rect_division - text_margin*2, bg_rect_h - emoji_total_side_length//2 - text_margin*2), spotlight_text)
    spotlight_text_pos = (bg_rect_pos[0]+bg_rect_division*current_div - (bg_rect_division//2) - scaled.width//2, bg_rect_pos[3]-(bg_rect_h - emoji_total_side_length//2)//2 - scaled.height//2)
    card_image.paste(scaled, spotlight_text_pos, scaled)

    #prepare scaled text
    current_div = 2
    
    username_font = ImageFont.truetype("resources/fonts/SourceSans3-Bold.ttf", size=100)
    username_text = user.name + "#" + user.discriminator
    scaled = scaled_text(username_font, (bg_rect_division-text_margin*2, CARD_SIZE[1]-text_margin*2), username_text)
    name_box_pos = (bg_rect_pos[0], profile_icon_pos[1]-scaled.height-text_margin*2, bg_rect_pos[0]+bg_rect_division-1, profile_icon_pos[1]-1)
    draw.rectangle(name_box_pos, fill=(0, 0, 0, OPACITY))
    card_image.paste(scaled, (bg_rect_pos[0]+(bg_rect_division//2)-(scaled.width//2), name_box_pos[1]+text_margin), scaled)

    total_levels = sum([x.BadgeEntry.levels for x in badges])
    stats_lines = (
        str(len(badges)) + ' Badges',
        str(total_levels) + ' Levels',
        'Joined ' + shorthand_time_elapsed(user.joined_at, datetime.now()) + ' ago'
    )
    stats_font = ImageFont.truetype("resources/fonts/SourceSans3-Regular.ttf", size=60)
    scaled = scaled_text(stats_font, (bg_rect_division-(text_margin*5//2), bg_rect_h), stats_lines)
    stats_text_pos = (bg_rect_pos[0]+bg_rect_division*(current_div-1) + text_margin, bg_rect_pos[1] + bg_rect_h//2 - scaled.height//2)
    card_image.paste(scaled, stats_text_pos, scaled)

    #draw.text(stats_text_pos, , font=stats_font)

    return card_image

def multiline_get_size(font, lines):
    if isinstance(lines, str):
        lines = [lines]
    y_size = 0
    x_sizes = []
    for line in lines:
        size = font.getsize(line)
        y_size += size[1]
        x_sizes.append(size[0])
    return (max(x_sizes), y_size)

#Gets the time elapsed from start to end in short format (i.e. 1y or 6m or 10d)
def shorthand_time_elapsed(start, end, *, top_only=True):
    delta = end - start
    total_time = delta.total_seconds()
    minutes, seconds = divmod(total_time, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    months, days = divmod(days, 31)
    years, months = divmod(months, 12)
    if top_only:
        if years > 0: return "%dy %dm" % (years, months) #Just for more granularity
        if months > 0: return "%dm %dd" % (months, days) #Just for more granularity
        if days > 0: return "%dd" % days
        if hours > 0: return "%dh" % hours
        if minutes > 0: return "%dm" % minutes
        if seconds > 0: return "%ds" % seconds
    return "%dy %dd %dh %dm %ds" % (years, days, hours, minutes, seconds)

def codepoint(codes):
    # See https://github.com/twitter/twemoji/issues/419#issuecomment-637360325
    if "200d" not in codes:
        return "-".join([c for c in codes if c != "fe0f"])
    return "-".join(codes)

#Returns an Image object of the specified emoji
async def get_emoji_image(bot, emoji, *, format=None, static_format='png'):
    custom_emoji = re.match(funcs.emoji_regex, emoji)
    if custom_emoji: #its a custom discord emoji
        emoji_id = custom_emoji.group(3)
        resolved_emoji = bot.get_emoji(int(emoji_id))
        asset = resolved_emoji.url_as(format=format, static_format=static_format)
        data = await asset.read()
        data = BytesIO(data)
    else: #its a grapheme/unicode emoji
        code = codepoint(["{0:x}".format(ord(c)) for c in emoji])
        target_url = TWEMOJI_BASE.format(codepoint=code)
        data = await http.download_media(target_url)
    return data

#Takes a font, max_size, and text and returns a bitmap of scaled text
def scaled_text(font, max_size, text):
    text_size = multiline_get_size(font, text)
    if isinstance(text, tuple) or isinstance(text, list):
        text = "\n".join(text)
    plate = Image.new("RGBA", text_size, (0, 0, 0,0 ))
    font_draw = ImageDraw.Draw(plate)
    font_draw.text((0,0), text, font=font)
    plate.thumbnail(max_size)
    plate = plate.crop(plate.getbbox())
    return plate

def aspect_resize(img, target_size):
    x, y = img.size
    tx, ty = target_size
    fx, fy = x/tx, y/ty #difference expressed as factor
    factor = 1/fx if fx < fy else 1/fy #if fx or fy < 1, it will pick whichever has to scale more, if either is > 1, it will scale less
    return img.resize((int(x*factor)+1, int(y*factor)+1))
