from os import stat, statvfs
from PIL import Image, ImageDraw, ImageOps, ImageFont

CARD_SIZE = (1190, 700)
OPACITY = int(0.6*255)

#all of this is horrible...
def make_profile_card(bg_img):
    card_image = Image.new("RGB", CARD_SIZE, "black")

    #actually retrieve bg_img sometime here
    bg_img = bg_img.convert("RGBA")
    bg_img = aspect_resize(bg_img, CARD_SIZE)
    bg_img.putalpha(int(0.75*255)) #make it 75% transparent
    card_image.paste(bg_img, (0,0))

    draw = ImageDraw.Draw(card_image, "RGBA")
    margin = 25 #pixels

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
    draw.rectangle(color_rect_pos, fill="yellow") #reuse the position from the last rect, but offset the vertical part so this one sits above

    #divider bar
    for i in range(num_divisions-1):
        div_bar_x = bg_rect_pos[0]+bg_rect_division*(i+1)
        draw.rectangle((div_bar_x, bg_rect_pos[1]+10, div_bar_x, bg_rect_pos[3]-10), fill="white")

    #profile icon
    current_div = 1
    profile_icon = Image.open("testicon.png")
    prof_side_length = bg_rect_division
    profile_icon = profile_icon.resize((prof_side_length, prof_side_length))
    profile_icon_pos = (bg_rect_pos[0], bg_rect_pos[1]+bg_rect_h-prof_side_length)
    card_image.paste(profile_icon, profile_icon_pos)

    #Spotlight
    current_div = 3
    emoji = Image.open("testemoji.png")
    emoji_border = 7
    emoji_side_length = 128
    emoji_total_side_length = emoji_side_length + emoji_border * 2
    emoji_x = int(margin + (bg_rect_division*current_div - bg_rect_division/2) - emoji_total_side_length/2)
    emoji_y = int((color_rect_pos[1] + color_rect_h//2) - emoji_total_side_length/2)
    emoji = emoji.resize((emoji_side_length, emoji_side_length))
    emoji = ImageOps.expand(emoji, emoji_border, fill="yellow")
    card_image.paste(emoji, (emoji_x, emoji_y))

    #prepare scaled text
    current_div = 2
    text_margin = 20
    username_font = ImageFont.truetype("SourceSans3-Bold.ttf", size=100)
    username_text = "Dankazie#2828"
    scaled = scaled_text(username_font, (bg_rect_division-text_margin*2, CARD_SIZE[1]-text_margin*2), username_text)
    name_box_pos = (bg_rect_pos[0], profile_icon_pos[1]-scaled.height-text_margin*2, bg_rect_pos[0]+bg_rect_division-1, profile_icon_pos[1]-1)
    draw.rectangle(name_box_pos, fill=(0, 0, 0, OPACITY))
    card_image.paste(scaled, (bg_rect_pos[0]+(bg_rect_division//2)-(scaled.width//2), name_box_pos[1]+text_margin), scaled)

    stats_lines = ('40 Badges', '25 Levels', 'Joined 2 years ago')
    stats_font = ImageFont.truetype("SourceSans3-Regular.ttf", size=60)
    scaled = scaled_text(stats_font, (bg_rect_division*2//3, bg_rect_h), stats_lines)
    stats_text_pos = (bg_rect_pos[0]+bg_rect_division*(current_div-1) + text_margin, bg_rect_pos[1] + bg_rect_h//2 - scaled.height//2)
    card_image.paste(scaled, stats_text_pos, scaled)
    
    #prepare spotlight text
    current_div = 3
    spotlight_text = "☢️ "
    spotlight_font = ImageFont.truetype("DejaVuSans.ttf", size=70)
    scaled = scaled_text(spotlight_font, (bg_rect_division - text_margin*2, bg_rect_h - emoji_total_side_length//2 - text_margin*2), spotlight_text)
    spotlight_text_pos = (bg_rect_pos[0]+bg_rect_division*current_div - (bg_rect_division//2) - scaled.width//2, bg_rect_pos[3]-(bg_rect_h - emoji_total_side_length//2)//2 - scaled.height//2)
    card_image.paste(scaled, spotlight_text_pos, scaled)
    #draw.text(stats_text_pos, , font=stats_font)

    

    card_image.show()
    card_image.save("card.jpg")

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


"""
    def add_text(image, text, location, font, fontsize=14, fontcolor=(0, 0, 0), 
                 border=0, border_color=(0, 0, 0), points=15):
        font_format = ImageFont.truetype(font, fontsize)
        drawer = ImageDraw.Draw(image)

        if border:
            (x, y) = location
            for step in range(0, math.floor(border * points), 1):
                angle = step * 2 * math.pi / math.floor(border * points)
                drawer.text((x - border * math.cos(angle), y - border * math.sin(angle)), text, border_color, font=font_format)
        drawer.text(location, text, fontcolor, font=font_format)
        return image
        """

if __name__ == "__main__":
    #bg_img = Image.open("profilecard.png")
    bg_img = Image.new("RGB", CARD_SIZE, (127, 127, 255))
    make_profile_card(bg_img)