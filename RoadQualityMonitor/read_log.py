
import os

import sys

log_file = sys.argv[1] if len(sys.argv) > 1 else 'android/build_error_10.2.0.log'

if not os.path.exists(log_file):
    print(f"File {log_file} not found.")
    exit(1)

print(f"Reading {log_file}...")
try:
    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
except Exception as e:
    # Try utf-16le if utf-8 fails or produces garbage (PowerShell redirect)
    try:
        with open(log_file, 'r', encoding='utf-16le', errors='replace') as f:
            content = f.read()
    except Exception as e2:
        print(f"Error reading file: {e2}")
        exit(1)

if "FAILED" in content or "Error" in content:
    print("Found error keywords in logs. Extracting context...")
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if "FAILED" in line or "What went wrong" in line or "Error" in line:
            print(f"Line {i}: {line}")
            # Print next 20 lines
            for j in range(1, 25):
                if i + j < len(lines):
                    print(lines[i+j])
            print("-" * 20)
else:
    print("No 'FAILED' found in logs. Printing last 50 lines:")
    print(content[-2000:])
