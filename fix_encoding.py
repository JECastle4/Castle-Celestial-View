#!/usr/bin/env python3
"""Fix UTF-8 encoding in test file open() calls."""

import re

# Fix test_benchmark_fixes.py
with open('tests/test_benchmark_fixes.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r"with open\(([^,]+), 'r'\)",
    r"with open(\1, 'r', encoding='utf-8')",
    content
)

with open('tests/test_benchmark_fixes.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed test_benchmark_fixes.py")

# Fix test_export_empty_contacts_fix.py
with open('tests/test_export_empty_contacts_fix.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r"with open\(([^,]+), 'r'\)",
    r"with open(\1, 'r', encoding='utf-8')",
    content
)

with open('tests/test_export_empty_contacts_fix.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed test_export_empty_contacts_fix.py")

# Fix test_metrics_label_extraction_fixed.py if it has the issue
try:
    with open('tests/test_metrics_label_extraction_fixed.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = re.sub(
        r"with open\(([^,]+), 'r'\)",
        r"with open(\1, 'r', encoding='utf-8')",
        content
    )
    
    with open('tests/test_metrics_label_extraction_fixed.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Fixed test_metrics_label_extraction_fixed.py")
except Exception as e:
    print(f"Skipped test_metrics_label_extraction_fixed.py: {e}")

print("\nAll files fixed!")
