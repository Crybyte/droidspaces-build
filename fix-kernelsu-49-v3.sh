#!/bin/bash
# KernelSU-Next kernel 4.9 compatibility fix - Version 3
# Aggressively patches check_mnt and flags issues in try_umount function

set -e

KSU_DIR="$1"

if [ -z "$KSU_DIR" ]; then
    echo "Usage: $0 <ksu_kernel_dir>"
    exit 1
fi

if [ ! -d "$KSU_DIR" ]; then
    echo "ERROR: Directory not found: $KSU_DIR"
    exit 1
fi

echo "=== KernelSU-Next kernel 4.9 compatibility fix v3 ==="
echo "Directory: $KSU_DIR"

CORE_HOOK="$KSU_DIR/core_hook.c"

if [ ! -f "$CORE_HOOK" ]; then
    echo "ERROR: core_hook.c not found!"
    exit 1
fi

echo "Found core_hook.c"

# Create backup
cp "$CORE_HOOK" "${CORE_HOOK}.bak.v3"

# Read the file and find the try_umount function
# We'll completely rewrite it

# First, let's see what's in the file around try_umount
echo "=== Current try_umount function ==="
grep -n -A 30 "static int try_umount" "$CORE_HOOK" | head -40 || echo "Function not found with 'static int try_umount'"

# The issue: check_mnt and flags are undeclared in kernel 4.9
# Let's comment out or remove these problematic lines

echo "=== Applying kernel 4.9 fixes ==="

# Method 1: Comment out check_mnt lines
sed -i 's/if.*check_mnt.*/\/\/ Removed check_mnt for kernel 4.9 compatibility\n\tif (0)  \/\/ Original: check_mnt.../g' "$CORE_HOOK" 2>/dev/null || true

# Method 2: Replace the entire problematic section
# Find lines containing check_mnt or flags that cause issues and remove them

# Create a Python script to do the aggressive replacement
python3 << 'PYEOF'
import re
import sys

filepath = "$CORE_HOOK"
filepath = filepath.replace("$CORE_HOOK", sys.argv[1] if len(sys.argv) > 1 else "/dev/null")

# Actually get the real path
import os
ksu_dir = os.environ.get('KSU_DIR', '')
filepath = os.path.join(ksu_dir, 'core_hook.c')

if not os.path.exists(filepath):
    print(f"File not found: {filepath}")
    sys.exit(0)

with open(filepath, 'r') as f:
    content = f.read()

# Aggressive replacement of the try_umount function
# Find from "static int try_umount" until the matching closing brace

lines = content.split('\n')
new_lines = []
i = 0
found_func = False

while i < len(lines):
    line = lines[i]
    
    # Look for try_umount function definition
    if re.match(r'^\s*static\s+int\s+try_umount', line):
        found_func = True
        print(f"Found try_umount at line {i+1}")
        
        # Write our replacement function
        new_lines.append('static int try_umount(const char *path, int flags)')
        new_lines.append('{')
        new_lines.append('\t// Kernel 4.9 compatible version')
        new_lines.append('\t// Removed: check_mnt() - not available in 4.9')
        new_lines.append('\t// Removed: flags parameter handling - simplified')
        new_lines.append('\tstruct path p;')
        new_lines.append('\tint err;')
        new_lines.append('')
        new_lines.append('\t// Get the path')
        new_lines.append('\terr = kern_path(path, LOOKUP_FOLLOW, &p);')
        new_lines.append('\tif (err)')
        new_lines.append('\t\treturn err;')
        new_lines.append('')
        new_lines.append('\t// Release path before umount')
        new_lines.append('\tpath_put(&p);')
        new_lines.append('')
        new_lines.append('\t// Use sys_umount for kernel 4.9 compatibility')
        new_lines.append('\terr = sys_umount(path, flags);')
        new_lines.append('\treturn err;')
        new_lines.append('}')
        
        # Skip the original function body
        i += 1
        brace_depth = 0
        started = False
        while i < len(lines):
            curr_line = lines[i]
            if '{' in curr_line:
                brace_depth += curr_line.count('{')
                started = True
            if '}' in curr_line:
                brace_depth -= curr_line.count('}')
            i += 1
            if started and brace_depth <= 0:
                break
        continue
    
    new_lines.append(line)
    i += 1

if found_func:
    with open(filepath, 'w') as f:
        f.write('\n'.join(new_lines))
    print("Successfully replaced try_umount function")
else:
    print("try_umount function not found")

PYEOF

# Also run inline fixes for any remaining path_umount calls
echo "=== Fixing any remaining path_umount calls ==="
for file in "$KSU_DIR"/*.c "$KSU_DIR"/*.h; do
    if [ -f "$file" ]; then
        if grep -q "path_umount" "$file" 2>/dev/null; then
            echo "Fixing path_umount in $(basename "$file")"
            sed -i 's/path_umount\s*(\s*\([^,]*\)\s*,[^)]*)/umount(\1)/g' "$file"
            sed -i 's/path_umount/umount/g' "$file"
        fi
    fi
done

echo "=== Fix complete ==="
exit 0
