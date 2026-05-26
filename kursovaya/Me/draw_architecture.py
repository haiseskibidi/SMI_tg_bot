import os
import sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')

output_img_path = r"C:\Users\Q1\Documents\SMI_tg_bot\kursovaya\Me\architecture_diagram.png"

# Setup image size and background
width, height = 900, 550
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
    # PIL draw.rounded_rectangle is available in newer Pillow versions
    try:
        draw.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=fill, outline=outline, width=width)
    except AttributeError:
        # Fallback to standard rectangle
        draw.rectangle([x1, y1, x2, y2], fill=fill, outline=outline, width=width)

def draw_arrow(draw, x1, y1, x2, y2, color=(80, 80, 80), width=2):
    draw.line([x1, y1, x2, y2], fill=color, width=width)
    # Simple arrowhead
    import math
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

# 1. DRAW SUBGRAPHS / GROUPS
# Group A: Core Orchestrator
draw_rounded_rect(draw, 50, 30, 480, 220, 10, fill=(253, 245, 255), outline=(214, 154, 229), width=2)
draw.text((65, 40), "Ядро системы (Core Orchestrator)", fill=(120, 40, 140), font=font_title)

# Group B: Modules
draw_rounded_rect(draw, 50, 280, 850, 420, 10, fill=(245, 248, 255), outline=(155, 178, 229), width=2)
draw.text((65, 290), "Активные модули сбора и вывода", fill=(40, 80, 160), font=font_title)

# 2. DRAW COMPONENT BOXES
# Inside Core:
# NewsMonitorWithBot
draw_rounded_rect(draw, 70, 75, 460, 125, 5, fill=(255, 255, 255), outline=(214, 154, 229), width=1)
draw.text((85, 90), "NewsMonitorWithBot (Главное управление)", fill=(0, 0, 0), font=font_bold)

# ConfigLoader
draw_rounded_rect(draw, 70, 145, 250, 205, 5, fill=(255, 255, 255), outline=(214, 154, 229), width=1)
draw.text((80, 165), "ConfigLoader (YAML)", fill=(50, 50, 50), font=font_text)

# LifecycleManager
draw_rounded_rect(draw, 280, 145, 460, 205, 5, fill=(255, 255, 255), outline=(214, 154, 229), width=1)
draw.text((290, 165), "LifecycleManager (Службы)", fill=(50, 50, 50), font=font_text)

# Modules:
# TelegramMonitor (Telethon)
draw_rounded_rect(draw, 70, 325, 380, 395, 5, fill=(240, 244, 255), outline=(155, 178, 229), width=2)
draw.text((85, 340), "TelegramMonitor (Telethon)", fill=(10, 40, 100), font=font_bold)
draw.text((85, 365), "MTProto API Client (Чтение каналов)", fill=(80, 80, 80), font=font_text)

# TelegramBot (Bot API)
draw_rounded_rect(draw, 490, 325, 830, 395, 5, fill=(240, 255, 240), outline=(155, 229, 155), width=2)
draw.text((505, 340), "TelegramBot (Bot API)", fill=(10, 100, 10), font=font_bold)
draw.text((505, 365), "HTTP Bot API (Команды и управление)", fill=(80, 80, 80), font=font_text)

# Storage:
# SQLite DB
draw_rounded_rect(draw, 360, 450, 600, 520, 8, fill=(255, 240, 240), outline=(229, 155, 155), width=2)
draw.text((385, 465), "СУБД SQLite (news_monitor.db)", fill=(120, 10, 10), font=font_bold)
draw.text((385, 488), "Хранение постов, хэшей и логов", fill=(80, 80, 80), font=font_text)

# External elements:
# Channels (Left External)
draw_rounded_rect(draw, 70, 450, 260, 520, 5, fill=(240, 240, 240), outline=(180, 180, 180), width=1)
draw.text((85, 475), "Каналы-доноры Telegram", fill=(100, 100, 100), font=font_bold)

# Admin (Right External)
draw_rounded_rect(draw, 640, 450, 830, 520, 5, fill=(240, 240, 240), outline=(180, 180, 180), width=1)
draw.text((655, 475), "Администратор СМИ", fill=(100, 100, 100), font=font_bold)

# 3. DRAW RELATIONSHIPS & ARROWS
# Core -> Config
draw_arrow(draw, 160, 125, 160, 145)
# Core -> Lifecycle
draw_arrow(draw, 370, 125, 370, 145)

# Core -> Modules links (from Core box bottom to modules top)
draw_arrow(draw, 220, 220, 220, 325)
draw_arrow(draw, 660, 280, 660, 325) # via app lifecycle
draw_arrow(draw, 400, 220, 550, 325)

# Monitor -> DB (Write posts)
draw_arrow(draw, 225, 395, 360, 460)
draw.text((220, 415), "Запись постов", fill=(120, 40, 40), font=font_text)

# Bot -> DB (Read posts / stats)
draw_arrow(draw, 580, 450, 580, 395)
draw.text((585, 415), "Чтение новостей", fill=(40, 100, 40), font=font_text)

# External links:
# Channels -> Monitor (Real-time updates)
draw_arrow(draw, 165, 450, 165, 395)
draw.text((90, 420), "События постов", fill=(80, 80, 80), font=font_text)

# Bot -> Admin (Status / Commands)
draw_arrow(draw, 735, 395, 735, 450)
draw.text((745, 415), "Дайджесты и меню", fill=(80, 80, 80), font=font_text)

# Save the generated PNG image
print(f"Saving drawn architecture diagram to {output_img_path}...")
img.save(output_img_path)
print("SUCCESS: Diagram drawn successfully!")
