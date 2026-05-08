import json
import re
from pathlib import Path


def reverse_string_with_placeholders(s):
    # Split on {placeholder} tokens, keeping the delimiters
    parts = re.split(r'(\{[^}]+\})', s)
    # Reverse the order of parts, and reverse each non-placeholder segment
    reversed_parts = [
        part if re.fullmatch(r'\{[^}]+\}', part) else part[::-1]
        for part in reversed(parts)
    ]
    return ''.join(reversed_parts)


def reverse_strings(obj):
    if isinstance(obj, dict):
        return {k: reverse_strings(v) for k, v in obj.items()}
    elif isinstance(obj, str):
        return reverse_string_with_placeholders(obj)
    else:
        return obj


if __name__ == '__main__':
    repo_root = Path(__file__).resolve().parent
    input_path = repo_root / 'frontend' / 'src' / 'locales' / 'en.json'
    output_path = repo_root / 'frontend' / 'src' / 'locales' / 'xx-reverse.json'

    with open(input_path, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    xx_reverse = reverse_strings(en_data)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(xx_reverse, f, ensure_ascii=False, indent=2)

    print('✓ Created xx-reverse.json with reversed strings')
    print('Sample reversals:')
    print(f'  "Load Data" → "{xx_reverse["buttons"]["loadData"]}"')
    print(f'  "Latitude" → "{xx_reverse["forms"]["labels"]["latitude"]}"')
    print(f'  "New Moon" → "{xx_reverse["astronomy"]["phaseNames"]["newMoon"]}"')
