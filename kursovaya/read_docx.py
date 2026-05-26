import zipfile
import xml.etree.ElementTree as ET
import os

def get_docx_text(path):
    try:
        with zipfile.ZipFile(path) as docx:
            xml_content = docx.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            paragraphs = []
            for p in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                texts = [node.text for node in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if node.text]
                if texts:
                    paragraphs.append(''.join(texts))
            return '\n'.join(paragraphs)
    except Exception as e:
        return f"Error reading {path}: {str(e)}"

# Read both documents
me_path = r"C:\Users\Q1\Documents\SMI_tg_bot\kursovaya\Me\Копаницкий_ЗКР (2).docx"
duo_path = r"C:\Users\Q1\Documents\SMI_tg_bot\kursovaya\My_Duo\Шакшуев_ЗКР (3).docx"

print("==================== ME (Копаницкий Захар) ====================")
if os.path.exists(me_path):
    text_me = get_docx_text(me_path)
    print(text_me)
    # Save as text for easy reference
    with open(r"C:\Users\Q1\Documents\SMI_tg_bot\kursovaya\Me\Копаницкий_ЗКР.txt", "w", encoding="utf-8") as f:
        f.write(text_me)
else:
    print(f"File not found: {me_path}")

print("\n\n==================== DUO (Шакшуев Роман) ====================")
if os.path.exists(duo_path):
    text_duo = get_docx_text(duo_path)
    print(text_duo)
    # Save as text for easy reference
    with open(r"C:\Users\Q1\Documents\SMI_tg_bot\kursovaya\My_Duo\Шакшуев_ЗКР.txt", "w", encoding="utf-8") as f:
        f.write(text_duo)
else:
    print(f"File not found: {duo_path}")
