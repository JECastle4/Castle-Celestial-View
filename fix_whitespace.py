#!/usr/bin/env python3
"""Remove trailing whitespace from files."""

files = ['api/cache.py', 'api/main.py']
for filepath in files:
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    # Remove trailing whitespace from each line
    fixed_lines = [
        line.rstrip() + '\n' if line.rstrip() else '\n'
        for line in lines
    ]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

    print(f"Fixed trailing whitespace in {filepath}")
