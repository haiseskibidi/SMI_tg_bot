import sys
import docx

sys.stdout.reconfigure(encoding='utf-8')

template_path = r"C:\Users\Q1\Documents\SMI_tg_bot\kursovaya\My_Duo\Титульный КР 2026.docx"
doc = docx.Document(template_path)

print("AVAILABLE PARAGRAPH STYLES IN TEMPLATE:")
print("-" * 50)
for idx, style in enumerate(doc.styles):
    if style.type == docx.enum.style.WD_STYLE_TYPE.PARAGRAPH:
        print(f"  {idx}: Name='{style.name}'")
