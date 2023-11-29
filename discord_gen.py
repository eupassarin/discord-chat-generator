import argparse
import re
import datetime
import math
import os
import shutil
import sys
from pilmoji import Pilmoji
from PIL import Image, ImageFont, ImageDraw 
from moviepy.editor import ImageSequenceClip
from moviepy.editor import AudioFileClip
from moviepy.editor import concatenate_videoclips
from moviepy.editor import CompositeAudioClip

IMAGE_WIDTH = 1777
IMAGE_MIN_HEIGHT = 231
LINE_HEIGHT = 80
LINE_MENTION_WIDTH = 7

PROFILE_PIC_WIDTH = 120

BACKGROUND_COLOR = (54,57,63,255)
BACKGROUND_MENTION_COLOR = (68,64,57)
LINE_MENTION_COLOR = (239,177,50)
MESSAGE_FONT_COLOR = (220,220,220)
MENTION_COLOR = (201,205,251)
MENTION_BACKGROUND_COLOR = (65,70,118)
MENTION_LEFT_LINE_COLOR = (239, 177, 50)
URL_LINK_COLOR = (5, 168, 252)

MESSAGE_X = 190
MESSAGE_Y_INIT = 130
MESSAGE_DY = LINE_HEIGHT

NAME_POSITION = (MESSAGE_X,53)
NAME_FONT_COLOR = (255,255,255,255)
NAME_FONT_SIZE = 50
NAME_FONT = ImageFont.truetype('fonts/whitneymedium.otf', NAME_FONT_SIZE)

TIME_POSITION_Y = 67 
TIME_FONT_COLOR = (180,180,180)
TIME_FONT_SIZE = 30
TIME_FONT = ImageFont.truetype('fonts/whitneymedium.otf', TIME_FONT_SIZE)

MESSAGE_FONT_SIZE = 50
MESSAGE_FONT = ImageFont.truetype('fonts/whitneybook.otf', MESSAGE_FONT_SIZE)

image_number = 0

DEFAULT_MOVIE_FPS = 2
NOTIFICATION_AUDIO = os.path.join('audios', 'notification.mp3')
movie = False
clips = []

def main():

    global movie

    parser = argparse.ArgumentParser(description='CLI to read parameters')
    parser.add_argument('-i', '--input', help='Input file path', required=True)
    parser.add_argument('-c', '--clear', help='Delete output folder', action='store_true')
    parser.add_argument('-m', '--movie', help='Generate movie', action='store_true')
    
    args = parser.parse_args()

    project_name = os.path.splitext(os.path.basename(args.input))[0]
    input_file = args.input
    output_folder = os.path.join('output', project_name)
    clear = args.clear
    movie = args.movie

    # Check if the input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return

    # Check if the output folder exists, create it if not
    # If the flag is set, delete the output folder
    if clear and os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Read input file
    with open(input_file, encoding="utf8") as f:
        lines = f.read().splitlines()

    # Get messages block
    messages_block = get_block_of_messages(lines)

    # Generate messages of each block
    for i, message_block in enumerate(messages_block):
        generate_images_for_each_block(i, message_block, output_folder)

    if movie:
        generate_movie_with_audio(project_name, output_folder)

def generate_movie_with_audio(project_name, output_folder):
    video = concatenate_videoclips(clips, method="compose")
    video.write_videofile(os.path.join(output_folder, f'{project_name}.mp4'), 
                          codec="libx264", audio_codec="aac")

def generate_images_for_each_block(block_number, message_block, output_folder):
    lines = []
    user = message_block[0].split(':')[1]
    time_of_message = message_block[1]
    for i, line in enumerate(message_block[2:]):
        lines.append(line)
        generate_image(block_number, user, time_of_message, lines, output_folder)

def generate_image(block_number, user, time_of_message, lines, output_folder):
    
    global image_number
    global movie
    global clips

    full_mention = is_full_mention(lines);
    template = Image.new(mode='RGBA', 
                         size=(IMAGE_WIDTH, IMAGE_MIN_HEIGHT 
                               + (LINE_HEIGHT * (len(lines) - 1))
                               + calculate_imported_images_height(lines)), 
                         color=define_background_color(lines))
    
    message_position = [MESSAGE_X, MESSAGE_Y_INIT];

    # Draw the messages
    for i, line in enumerate(lines):
        line = line.split('-->')[0];
        if line[0] == '@':
            generate_line_with_mention(message_position, template, i, line, full_mention)
            message_position[1] += MESSAGE_DY
        elif line.startswith('[image:'):
            message_position = generate_imported_image(message_position, template, i, line)
        elif line.startswith('[url:'):
            with Pilmoji(template) as pilmoji:
                url = line[5:len(line)-1]
                pilmoji.text(message_position, url, URL_LINK_COLOR, font=MESSAGE_FONT)
            message_position[1] += MESSAGE_DY
        else:
            with Pilmoji(template) as pilmoji:
                pilmoji.text(message_position, line.strip(), MESSAGE_FONT_COLOR, font=MESSAGE_FONT)
            message_position[1] += MESSAGE_DY
    
    generate_profile_picture_name_time(template, user, time_of_message)

    draw = ImageDraw.Draw(template)
    if full_mention:
        draw.rectangle((0, 0, 
                        LINE_MENTION_WIDTH, message_position[1] + (MESSAGE_DY * 0.25)), 
                        fill=LINE_MENTION_COLOR)

    image_path = f'{output_folder}/{block_number:03d}-{image_number:03d}{user}.png'
    print(f'Generating image {image_path}')
    template.save(image_path)
    image_number += 1

    if movie:
        add_movie_clip(lines, image_path)

def add_movie_clip(lines, image_path):
    movie_fps = DEFAULT_MOVIE_FPS
    if "-->" in lines[-1]:
        movie_fps = float(lines[-1].split('-->')[1].strip())
    movie_fps = movie_fps
    clip_image = ImageSequenceClip([image_path], fps=1/movie_fps)
    audio_clip1 = AudioFileClip(NOTIFICATION_AUDIO)
    clips.append(clip_image.set_audio(audio_clip1))

def generate_imported_image(message_position, template, i, line):
    mask_radius = 12
    image = Image.open(os.path.join('images', line[7:len(line.strip())-1]))
    mask = Image.new("L", image.size, 0)
    draw_image = ImageDraw.Draw(mask)
    image_with_alpha = image.convert("RGBA")
    image_with_alpha.putalpha(mask)
    image.thumbnail(image_with_alpha.size, Image.Resampling.LANCZOS)
    draw_image.rounded_rectangle([(mask_radius, 0), (image.width - mask_radius, image.height)], radius=mask_radius, fill=255)
    template.paste(image, (message_position[0],message_position[1]), mask)
    message_position[0] = MESSAGE_X;
    message_position[1] += math.floor(image.size[1])
    return message_position[0:2]

def generate_line_with_mention(message_position, template, i, line, full_mention):
    draw = ImageDraw.Draw(template)
    user_ref  = line.split(' ')[0]
    content = line[len(user_ref):]
    text_bbox = draw.textbbox((0, 0), user_ref, font=MESSAGE_FONT)
    user_text_width = text_bbox[2] - text_bbox[0]
    user_text_height = text_bbox[3] - text_bbox[1]
    text_x, text_y = message_position
    
    # Mention rectangle
    
    # Background full line
    draw.rectangle((LINE_MENTION_WIDTH,  message_position[1], 
                   IMAGE_WIDTH, message_position[1] + (MESSAGE_DY * 0.85)), 
                   fill=BACKGROUND_MENTION_COLOR)
    # Left line
    draw.rectangle((0,  message_position[1], 
                    LINE_MENTION_WIDTH, message_position[1] + (MESSAGE_DY * 0.85)), 
                    fill=LINE_MENTION_COLOR)
    # Background name
    user_mention_position = (text_x, text_y+10, text_x + user_text_width, text_y + user_text_height + 12)
    draw.rectangle(user_mention_position, fill=MENTION_BACKGROUND_COLOR)
    
    # Draw the text on the rectangle
    with Pilmoji(template) as pilmoji:
        pilmoji.text(message_position, user_ref, MENTION_COLOR, font=NAME_FONT)
        pilmoji.text(
            (message_position[0] + user_text_width, message_position[1]), 
            content, MESSAGE_FONT_COLOR, font=MESSAGE_FONT)

def generate_profile_picture_name_time(template, user, time_of_message):
    profile_folder = "profiles"
    files = os.listdir(profile_folder)   
    pattern = re.compile(rf'{user}-(\w+\_\w+\_\w+)\.jpeg')
    matching_files = [file for file in files if pattern.match(file)]
    if matching_files:
        filename = matching_files[0]
        name_color = tuple(map(int, filename.split('-')[1].split('.')[0].split('_')))
    else:
        filename = f'{user}.jpeg'
        name_color = NAME_FONT_COLOR

    profile_picture = Image.open(os.path.join(profile_folder, filename))
    profile_picture.thumbnail([sys.maxsize, PROFILE_PIC_WIDTH], Image.Resampling.LANCZOS)
    mask = Image.new("L", profile_picture.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([(0, 0), (PROFILE_PIC_WIDTH, PROFILE_PIC_WIDTH)], fill=255)
    template.paste(profile_picture, (36, 45), mask)

    # Draw the name
    draw_name = ImageDraw.Draw(template)
    draw_name.text(NAME_POSITION, user, name_color, font=NAME_FONT)

    draw_time = ImageDraw.Draw(template)
    time_position = (NAME_POSITION[0] + NAME_FONT.getlength(user) + 25, TIME_POSITION_Y)  
    draw_time.text(time_position, f'Hoje às {time_of_message}', TIME_FONT_COLOR, font=TIME_FONT)

def get_block_of_messages(lines):
    messages_block = []
    messages = []
    for line in lines:
        if line == '' or line[0] == '#':
            continue
        if line.startswith(':'):
            if messages:
                messages_block.append(messages)
            messages = []
            messages.append(line)
            messages.append(datetime.datetime.now().strftime("%H:%M"))
        else:
            messages.append(line)
    
    if messages:
        messages_block.append(messages)
    
    return messages_block

def define_background_color(lines):
    # Check if there is  mention in the first line
    if is_full_mention(lines):
        return BACKGROUND_MENTION_COLOR
    return BACKGROUND_COLOR

def is_full_mention(lines):
    return lines[0][0] == '@'

def calculate_imported_images_height(lines):
    images_height = 0
    for i, line in enumerate(lines):
         if line.startswith('[image:'):
            line = line.split('-->')[0];
            image = Image.open(os.path.join('images', line[7:len(line.strip())-1]))
            images_height += (image.size[1] - LINE_HEIGHT)
    return images_height

if __name__ == "__main__":
    main()