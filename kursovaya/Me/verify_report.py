import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

report_path = r"C:\Users\Q1\Documents\SMI_tg_bot\kursovaya\Me\Копаницкий_КР_Отчет.md"

if not os.path.exists(report_path):
    print(f"Error: report file {report_path} not found!")
    sys.exit(1)

with open(report_path, "r", encoding="utf-8") as f:
    text = f.read()

words = text.split()
word_count = len(words)
char_count = len(text)

# Let's verify mandatory sections
sections = [
    "Введение",
    "1 Проектирование системы",
    "2 Реализация проекта",
    "Заключение",
    "Список литературы",
    "Приложение А. Руководство по развертыванию и запуску"
]

print("--- VERIFICATION REPORT ---")
print(f"Word Count: {word_count}")
print(f"Character Count: {char_count}")
print(f"Estimated Pages (assuming 300 words per page): {word_count / 300:.1f}")

missing = []
for s in sections:
    if s in text:
        print(f"✅ Section found: '{s}'")
    else:
        print(f"❌ Missing Section: '{s}'")
        missing.append(s)

if not missing:
    print("STATUS: VERIFICATION SUCCESSFUL! All standard sections exist.")
else:
    print(f"STATUS: FAILED. Missing sections: {missing}")
