import os
import sys
import math
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')

output_img_path = r"C:\Users\Q1\Documents\SMI_tg_bot\kursovaya\Me\algorithm_diagram.png"

# Setup image size and background
width, height = 900, 650
img = Image.new("RGB", (width, height), "white")
draw = ImageDraw.Draw(img)

# Try loading Windows system fonts, fall back to default if unavailable
try:
    font_path = r"C:\Windows\Fonts\arial.ttf"
    font_title = ImageFont.truetype(font_path, 16)
    font_text = ImageFont.truetype(font_path, 13)
    font_bold = ImageFont.truetype(font_path, 13)
except IOError:
    font_title = ImageFont.load_default()
    font_text = ImageFont.load_default()
    font_bold = ImageFont.load_default()

def draw_rounded_rect(draw, x1, y1, x2, y2, r, fill, outline, width=2):
    try:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill, outline=outline, width=width)
    except AttributeError:
        draw.rectangle([x1, y1, x2, y2], fill=fill, outline=outline, width=width)

def draw_arrow(draw, x1, y1, x2, y2, color=(80, 80, 80), width=2):
    draw.line([x1, y1, x2, y2], fill=color, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_len = 10
    arrow_angle = math.radians(30)
    
    ax1 = x2 - arrow_len * math.cos(angle - arrow_angle)
    ay1 = y2 - arrow_len * math.sin(angle - arrow_angle)
    ax2 = x2 - arrow_len * math.cos(angle + arrow_angle)
    ay2 = y2 - arrow_len * math.sin(angle + arrow_angle)
    
    draw.polygon([x2, y2, ax1, ay1, ax2, ay2], fill=color)

def draw_diamond(draw, xc, yc, w, h, fill, outline, width=2):
    points = [
        (xc, yc - h/2),  # Top
        (xc + w/2, yc),  # Right
        (xc, yc + h/2),  # Bottom
        (xc - w/2, yc)   # Left
    ]
    draw.polygon(points, fill=fill, outline=outline)
    # Re-draw outline with specified width since polygon outline defaults to 1px
    draw.line([points[0], points[1], points[2], points[3], points[0]], fill=outline, width=width)

# 1. DRAW NODES

# Node A: Start (Rounded Rect)
# "Поступило сообщение от @channel_username"
draw_rounded_rect(draw, 250, 30, 650, 80, 8, fill=(245, 248, 255), outline=(155, 178, 229), width=2)
draw.text((290, 46), "Поступило сообщение от @channel_username", fill=(0, 0, 0), font=font_bold)

# Node B: Decision 1 (Diamond)
# "Есть ли канал в config/channels_config.yaml?"
draw_diamond(draw, 450, 170, 380, 100, fill=(255, 248, 240), outline=(229, 178, 155), width=2)
draw.text((295, 152), "Есть ли канал в конфигурационном", fill=(0, 0, 0), font=font_text)
draw.text((320, 172), "файле channels_config.yaml?", fill=(0, 0, 0), font=font_text)

# Node C: Process 1 (Rect, Left)
# "Присвоить регион из явного списка"
draw_rounded_rect(draw, 100, 265, 340, 325, 5, fill=(240, 255, 240), outline=(155, 229, 155), width=2)
draw.text((120, 285), "Присвоить регион из явного списка", fill=(0, 0, 0), font=font_bold)

# Node D: Decision 2 (Diamond, Right)
# "Есть ли совпадение по ключевым словам в имени username?"
draw_diamond(draw, 640, 295, 380, 100, fill=(255, 248, 240), outline=(229, 178, 155), width=2)
draw.text((495, 277), "Есть ли совпадение по ключевым", fill=(0, 0, 0), font=font_text)
draw.text((485, 297), "словам в имени или описании канала?", fill=(0, 0, 0), font=font_text)

# Node E: Process 2 (Rect, Middle)
# "Присвоить регион по ключевому слову"
draw_rounded_rect(draw, 370, 415, 600, 475, 5, fill=(240, 255, 240), outline=(155, 229, 155), width=2)
draw.text((380, 435), "Присвоить регион по ключу", fill=(0, 0, 0), font=font_bold)

# Node F: Process 3 (Rect, Right)
# "Присвоить резервный регион 'general'"
draw_rounded_rect(draw, 640, 415, 870, 475, 5, fill=(250, 250, 250), outline=(180, 180, 180), width=2)
draw.text((650, 435), "Присвоить регион \"general\"", fill=(80, 80, 80), font=font_bold)

# Node G: End (Rounded Rect)
# "Отправить новость в топик с соответствующим thread_id"
draw_rounded_rect(draw, 240, 540, 660, 595, 8, fill=(253, 245, 255), outline=(214, 154, 229), width=2)
draw.text((275, 558), "Отправить новость в топик с соответствующим thread_id", fill=(120, 40, 140), font=font_bold)


# 2. DRAW CONNECTORS & LABELS

# Arrow A -> B
draw_arrow(draw, 450, 80, 450, 120)

# Arrow B -> C (Yes)
# Draw diagonal
draw_arrow(draw, 260, 170, 220, 265)
draw.text((205, 195), "Да (Приоритет 1)", fill=(10, 100, 10), font=font_bold)

# Arrow B -> D (No)
# Draw diagonal
draw_arrow(draw, 640, 170, 640, 245)
draw.text((650, 195), "Нет", fill=(100, 10, 10), font=font_bold)

# Arrow D -> E (Yes)
draw_arrow(draw, 450, 295, 485, 415)
draw.text((435, 345), "Да (Приоритет 2)", fill=(10, 100, 10), font=font_bold)

# Arrow D -> F (No)
draw_arrow(draw, 830, 295, 755, 415)
draw.text((805, 345), "Нет (Резерв)", fill=(100, 10, 10), font=font_bold)


# Connectors to End (G)
# C -> G (Orthogonal path)
# (220, 325) down to (220, 505) right to (330, 505) down to (330, 540)
draw.line([(220, 325), (220, 505), (330, 505), (330, 540)], fill=(80, 80, 80), width=2)
draw_arrow(draw, 330, 530, 330, 540)

# E -> G
# (485, 475) down to (450, 540)
draw_arrow(draw, 485, 475, 450, 540)

# F -> G
# (755, 475) down to (755, 505) left to (570, 505) down to (570, 540)
draw.line([(755, 475), (755, 505), (570, 505), (570, 540)], fill=(80, 80, 80), width=2)
draw_arrow(draw, 570, 530, 570, 540)

# Save the generated PNG image
print(f"Saving drawn algorithm diagram to {output_img_path}...")
img.save(output_img_path)
print("SUCCESS: Algorithm diagram drawn successfully!")
