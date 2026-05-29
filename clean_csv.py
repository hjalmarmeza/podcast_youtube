import re

input_file = '/Users/hjalmarmeza/.gemini/antigravity/brain/8be42c90-9a6d-4970-9901-576dfa4a7680/.system_generated/steps/52/content.md'
output_file = '/Users/hjalmarmeza/Downloads/Antigravity/Posible proyecto/metadata.csv'

with open(input_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

clean_lines = []
csv_started = False

for line in lines:
    # Remove the line number prefix (e.g., "9: N°,Serie Temática...")
    match = re.match(r'^\d+:\s*(.*)', line)
    if match:
        clean_line = match.group(1)
        if clean_line.startswith('N°,Serie Temática'):
            csv_started = True
        
        if csv_started:
            clean_lines.append(clean_line)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(clean_lines))

print(f"CSV limpiado y guardado en {output_file}")
