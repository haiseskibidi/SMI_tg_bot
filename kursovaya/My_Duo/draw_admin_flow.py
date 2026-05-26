import os
import sys
from PIL import Image, ImageDraw, ImageFont
import math

sys.stdout.reconfigure(encoding='utf-8')

output_img_path = r"C:\Users\Q1\Documents\SMI_tg_bot\kursovaya\My_Duo\admin_flowchart.png"
output_dir = os.path.dirname(output_img_path)
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Setup image size and background
width, height = 980, 620
img = Image.new("RGB", (width, height), "white")
draw = ImageDraw.Draw(img)

# Try loading Windows system fonts, fall back to default if unavailable
try:
    font_path = r"C:\Windows\Fonts\arial.ttf"
    font_title = ImageFont.truetype(font_path, 16)
    font_text = ImageFont.truetype(font_path, 13)
    font_bold = ImageFont.truetype(font_path, 13)
    font_small = ImageFont.truetype(font_path, 11)
except IOError:
    font_title = ImageFont.load_default()
    font_text = ImageFont.load_default()
    font_bold = ImageFont.load_default()
    font_small = ImageFont.load_default()

def draw_rounded_rect(draw, x1, y1, x2, y2, r, fill, outline, width=2):
    try:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill, outline=outline, width=width)
    except AttributeError:
        draw.rectangle([x1, y1, x2, y2], fill=fill, outline=outline, width=width)

def draw_diamond(draw, cx, cy, w, h, fill, outline, width=2):
    x1, y1 = cx, cy - h/2
    x2, y2 = cx + w/2, cy
    x3, y3 = cx, cy + h/2
    x4, y4 = cx - w/2, cy
    draw.polygon([x1, y1, x2, y2, x3, y3, x4, y4], fill=fill, outline=outline)

def draw_arrow(draw, x1, y1, x2, y2, color=(80, 80, 80), width=2):
    draw.line([x1, y1, x2, y2], fill=color, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_len = 10
    arrow_angle = math.radians(30)
    
    # Left wing
    ax1 = x2 - arrow_len * math.cos(angle - arrow_angle)
    ay1 = y2 - arrow_len * math.sin(angle - arrow_angle)
    # Right wing
    ax2 = x2 - arrow_len * math.cos(angle + arrow_angle)
    ay2 = y2 - arrow_len * math.sin(angle + arrow_angle)
    
    draw.polygon([x2, y2, ax1, ay1, ax2, ay2], fill=color)

# 1. DRAW HEADERS & LABELS
draw.text((30, 20), "Telegram-Бот: Архитектура UI и маршрутизация административных команд", fill=(20, 60, 120), font=font_title)
draw.line([30, 45, 950, 45], fill=(200, 200, 200), width=1)

# 2. DRAW FLOW BOXES

# Node 1: Entry Point (User request)
# (Center around X=490)
draw_rounded_rect(draw, 340, 60, 640, 110, 5, fill=(245, 245, 245), outline=(160, 160, 160), width=1)
draw.text((355, 75), "Входной запрос (Команда / callback)", fill=(0, 0, 0), font=font_bold)

# Node 2: Authorization Diamond (Is Admin?)
draw_diamond(draw, 490, 185, 220, 90, fill=(255, 245, 235), outline=(235, 140, 60), width=2)
draw.text((435, 170), "chat_id в ADMIN_IDS?", fill=(120, 50, 0), font=font_bold)

# Node 3: Unauthorized Access (Left of Diamond)
draw_rounded_rect(draw, 60, 160, 260, 210, 5, fill=(255, 240, 240), outline=(220, 100, 100), width=2)
draw.text((75, 175), "Доступ заблокирован", fill=(150, 20, 20), font=font_bold)
draw.text((75, 192), "Игнорирование / Ошибка", fill=(150, 20, 20), font=font_small)

# Node 4: UpdateProcessor (Core Router)
draw_rounded_rect(draw, 340, 280, 640, 330, 5, fill=(245, 245, 255), outline=(140, 140, 220), width=2)
draw.text((395, 295), "UpdateProcessor (Маршрутизатор)", fill=(20, 20, 120), font=font_bold)

# Node 5: Commands Branch (Left of Router)
draw_rounded_rect(draw, 140, 370, 390, 420, 5, fill=(255, 255, 255), outline=(140, 140, 220), width=1)
draw.text((155, 385), "Командный обработчик (Command)", fill=(50, 50, 50), font=font_text)

# Node 6: Callbacks Branch (Right of Router)
draw_rounded_rect(draw, 590, 370, 840, 420, 5, fill=(255, 255, 255), outline=(140, 140, 220), width=1)
draw.text((605, 385), "Callback-обработчик (Callback)", fill=(50, 50, 50), font=font_text)

# Managers layer:
# Manager 1: BasicCommands
draw_rounded_rect(draw, 40, 470, 240, 530, 5, fill=(245, 255, 245), outline=(100, 200, 100), width=2)
draw.text((55, 485), "BasicCommands", fill=(10, 80, 10), font=font_bold)
draw.text((55, 505), "/start, /status, /digest", fill=(100, 100, 100), font=font_small)

# Manager 2: ManagementCommands
draw_rounded_rect(draw, 270, 470, 470, 530, 5, fill=(245, 255, 245), outline=(100, 200, 100), width=2)
draw.text((285, 485), "ManagementCommands", fill=(10, 80, 10), font=font_bold)
draw.text((285, 505), "Управление каналами и БД", fill=(100, 100, 100), font=font_small)

# Manager 3: RegionCallbacks
draw_rounded_rect(draw, 500, 470, 700, 530, 5, fill=(245, 255, 245), outline=(100, 200, 100), width=2)
draw.text((515, 485), "RegionCallbacks", fill=(10, 80, 10), font=font_bold)
draw.text((515, 505), "Выбор регионов подписки", fill=(100, 100, 100), font=font_small)

# Manager 4: ChannelCallbacks
draw_rounded_rect(draw, 730, 470, 930, 530, 5, fill=(245, 255, 245), outline=(100, 200, 100), width=2)
draw.text((745, 485), "ChannelCallbacks", fill=(10, 80, 10), font=font_bold)
draw.text((745, 505), "Добавление/удаление каналов", fill=(100, 100, 100), font=font_small)

# Node 7: Database & Config (Bottom Center)
draw_rounded_rect(draw, 340, 560, 640, 610, 5, fill=(255, 240, 240), outline=(220, 100, 100), width=2)
draw.text((365, 575), "СУБД SQLite (news_monitor.db) & .env", fill=(120, 20, 20), font=font_bold)

# 3. DRAW RELATIONSHIPS & ARROWS
# Entry -> Is Admin?
draw_arrow(draw, 490, 110, 490, 140)

# Is Admin? -> NO -> Unauthorized Alert
draw_arrow(draw, 380, 185, 260, 185)
draw.text((310, 165), "Нет", fill=(150, 20, 20), font=font_bold)

# Is Admin? -> YES -> Router
draw_arrow(draw, 490, 230, 490, 280)
draw.text((500, 245), "Да", fill=(10, 100, 10), font=font_bold)

# Router -> Commands
draw_arrow(draw, 340, 305, 265, 305)
draw_arrow(draw, 265, 305, 265, 370)
draw.text((210, 315), "Команды", fill=(80, 80, 80), font=font_small)

# Router -> Callbacks
draw_arrow(draw, 640, 305, 715, 305)
draw_arrow(draw, 715, 305, 715, 370)
draw.text((670, 315), "Callback-клик", fill=(80, 80, 80), font=font_small)

# Commands -> Managers 1 & 2
draw_arrow(draw, 265, 420, 140, 470)
draw_arrow(draw, 265, 420, 370, 470)

# Callbacks -> Managers 3 & 4
draw_arrow(draw, 715, 420, 600, 470)
draw_arrow(draw, 715, 420, 830, 470)

# Managers -> DB (Access)
# Draw lines from managers to database
draw_arrow(draw, 140, 530, 340, 575)
draw_arrow(draw, 370, 530, 420, 560)
draw_arrow(draw, 600, 530, 560, 560)
draw_arrow(draw, 830, 530, 640, 575)

# Save the generated PNG image
print(f"Saving drawn flowchart to {output_img_path}...")
img.save(output_img_path)
print("SUCCESS: Flowchart drawn successfully!")
