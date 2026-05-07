import json
import re

# Read the API locale file
with open('api/locales/en.json', 'r', encoding='utf-8') as f:
    en_data = json.load(f)

def reverse_string(s):
    """Reverse a string while keeping {placeholder} tokens intact."""
    # Split on {identifier} tokens, keeping the delimiters
    parts = re.split(r'(\{[^}]+\})', s)
    # Reverse the sequence of parts, then reverse each non-placeholder text segment
    parts.reverse()
    return ''.join(
        part if re.match(r'^\{[^}]+\}$', part) else part[::-1]
        for part in parts
    )

# Function to reverse strings recursively
def reverse_strings(obj):
    if isinstance(obj, dict):
        return {k: reverse_strings(v) for k, v in obj.items()}
    elif isinstance(obj, str):
        return reverse_string(obj)
    else:
        return obj

# Create reversed version
xx_reverse = reverse_strings(en_data)

# Write to file
with open('api/locales/xx-reverse.json', 'w', encoding='utf-8') as f:
    json.dump(xx_reverse, f, ensure_ascii=False, indent=2)

print('Created api/locales/xx-reverse.json')
print('Sample phase names:')
print(f'  New Moon: {xx_reverse["moonPhases"]["newMoon"]}')
print(f'  Full Moon: {xx_reverse["moonPhases"]["fullMoon"]}')
