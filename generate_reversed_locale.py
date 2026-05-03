import json

# Read the English locale
with open('frontend/src/locales/en.json', 'r', encoding='utf-8') as f:
    en_data = json.load(f)

# Function to reverse strings recursively
def reverse_strings(obj):
    if isinstance(obj, dict):
        return {k: reverse_strings(v) for k, v in obj.items()}
    elif isinstance(obj, str):
        return obj[::-1]  # Reverse the string
    else:
        return obj

# Create reversed version
xx_reverse = reverse_strings(en_data)

# Write to file
with open('frontend/src/locales/xx-reverse.json', 'w', encoding='utf-8') as f:
    json.dump(xx_reverse, f, ensure_ascii=False, indent=2)

print('✓ Created xx-reverse.json with reversed strings')
print('Sample reversals:')
print(f'  "Load Data" → "{xx_reverse["buttons"]["loadData"]}"')
print(f'  "Latitude" → "{xx_reverse["forms"]["labels"]["latitude"]}"')
print(f'  "New Moon" → "{xx_reverse["astronomy"]["phaseNames"]["newMoon"]}"')
