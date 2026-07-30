import json
import re
from pathlib import Path


def reverse_string(s):
    """Reverse a string while keeping {placeholder} tokens intact."""
    parts = re.split(r'(\{[^}]+\})', s)
    parts.reverse()
    return ''.join(
        part if re.match(r'^\{[^}]+\}$', part) else part[::-1]
        for part in parts
    )


def reverse_strings(obj):
    if isinstance(obj, dict):
        return {k: reverse_strings(v) for k, v in obj.items()}
    elif isinstance(obj, str):
        return reverse_string(obj)
    else:
        return obj


if __name__ == '__main__':
    repo_root = Path(__file__).resolve().parent
    input_path = repo_root / 'api' / 'locales' / 'en.json'
    output_path = repo_root / 'api' / 'locales' / 'xx-reverse.json'

    with open(input_path, 'r', encoding='utf-8') as f:
        en_data = json.load(f)

    xx_reverse = reverse_strings(en_data)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(xx_reverse, f, ensure_ascii=False, indent=2)

    print('Created api/locales/xx-reverse.json')
    print('Sample phase names:')
    print(f'  New Moon: {xx_reverse["moonPhases"]["newMoon"]}')
    print(f'  Full Moon: {xx_reverse["moonPhases"]["fullMoon"]}')
