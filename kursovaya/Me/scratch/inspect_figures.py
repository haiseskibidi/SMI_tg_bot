import sys
import docx

sys.stdout.reconfigure(encoding='utf-8')

user_doc_path = r"C:\Users\Q1\Documents\SMI_tg_bot\kursovaya\Me\ОТЧЁТ.docx"
doc = docx.Document(user_doc_path)

print("FIGURE CAPTIONS AND TEXT IN USER'S DOC:")
print("-" * 60)
fig_count = 0
for idx, p in enumerate(doc.paragraphs):
    text = p.text.strip()
    if not text:
        continue
    
    # Check if this paragraph contains figure caption text
    if "рисунок" in text.lower() or "рис. " in text.lower():
        fig_count += 1
        pf = p.paragraph_format
        print(f"\nFigure/Caption Paragraph #{idx} [Style: {p.style.name}]:")
        print(f"  Text: '{text}'")
        print(f"  Align: {p.alignment} | LineSpacing: {pf.line_spacing} | FirstIndent: {pf.first_line_indent.cm if pf.first_line_indent else 0:.2f} cm")
        print(f"  SpaceBefore: {pf.space_before.pt if pf.space_before else 0:.2f} pt | SpaceAfter: {pf.space_after.pt if pf.space_after else 0:.2f} pt")
        print(f"  Runs:")
        for r_idx, r in enumerate(p.runs):
            print(f"    Run {r_idx}: '{r.text}' | font={r.font.name} | size={r.font.size.pt if r.font.size else None} | B={r.bold} | I={r.italic}")

print(f"\nTotal Figure/Caption paragraphs found: {fig_count}")
