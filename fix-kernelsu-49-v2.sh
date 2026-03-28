#!/bin/bash
# fix-kernelsu-49-v2.sh - Aggressive KernelSU-Next v1.0.7 kernel 4.9 compatibility fixes
set -e

KSU_KERNEL_DIR="$1"
if [ -z "$KSU_KERNEL_DIR" ]; then
    echo "Usage: $0 <path_to_kernelsu_kernel_directory>"
    exit 1
fi

if [ ! -d "$KSU_KERNEL_DIR" ]; then
    echo "ERROR: Directory $KSU_KERNEL_DIR does not exist"
    exit 1
fi

echo "=== Applying AGGRESSIVE kernel 4.9 compatibility patches ==="

# Fix 1: Replace path_umount with umount
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        if grep -q "path_umount" "$file" 2>/dev/null; then
            echo "Patching path_umount in $(basename "$file")..."
            sed -i 's/path_umount\s*(\s*\([^,]*\)\s*,[^)]*)/umount(\1)/g' "$file"
            sed -i 's/path_umount/umount/g' "$file"
        fi
    fi
done

# Fix 2: Fix KERNEL_VERSION calls
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        if grep -q 'KERNEL_VERSION\s*(\s*[0-9]\+\s*,\s*[0-9]\+\s*)' "$file" 2>/dev/null; then
            echo "Patching KERNEL_VERSION in $(basename "$file")..."
            sed -i 's/KERNEL_VERSION\s*(\s*\([0-9]\+\)\s*,\s*\([0-9]\+\)\s*)/KERNEL_VERSION(\1, \2, 0)/g' "$file"
        fi
    fi
done

# Fix 3: CRITICAL - Completely rewrite try_umount function in core_hook.c
CORE_HOOK="$KSU_KERNEL_DIR/core_hook.c"
if [ -f "$CORE_HOOK" ]; then
    echo "Applying CRITICAL try_umount fix to core_hook.c..."
    
    # Create a Python script to do the replacement (more reliable than sed/awk for complex replacements)
    python3 << 'PYTHON_SCRIPT'
import re

with open("'$CORE_HOOK'", "r") as f:
    content = f.read()

# Pattern to match the entire try_umount function
# Look for: static int try_umount(struct path *path, ...)
old_function_pattern = r'static int try_umount\(struct path \*path[^)]*\)\s*\{[^}]*\{[^}]*\}[^}]*\}'

# New function that works with kernel 4.9
new_function = '''static int try_umount(struct path *path)
{
	int err = 0;
	struct mount *mnt = real_mount(path->mnt);
	if (!should_umount(mnt)) {
		return -EBUSY;
	}
	err = umount(path);
	return err;
}'''

# Try to replace the function
match = re.search(old_function_pattern, content, re.DOTALL)
if match:
    content = content[:match.start()] + new_function + content[match.end():]
    with open("'$CORE_HOOK'", "w") as f:
        f.write(content)
    print("Successfully replaced try_umount function")
else:
    print("Could not match function with regex, trying alternative approach...")
    
    # Alternative: Replace any references to check_mnt and flags variables
    # by removing lines that use them
    lines = content.split('\n')
    new_lines = []
    skip_next = False
    for line in lines:
        if 'check_mnt' in line or (line.strip().startswith('if') and 'check_mnt' in line):
            # Skip lines containing check_mnt
            continue
        if line.strip() == 'flags' or 'flags)' in line:
            # Skip lines with undeclared flags
            continue
        new_lines.append(line)
    
    content = '\n'.join(new_lines)
    with open("'$CORE_HOOK'", "w") as f:
        f.write(content)
    print("Applied alternative fix")
PYTHON_SCRIPT

    # Also fix any 2-argument try_umount calls
    if grep -q 'try_umount\s*([^,]*,[^)]*)' "$CORE_HOOK" 2>/dev/null; then
        echo "Patching try_umount calls to use 1 argument..."
        sed -i 's/try_umount\s*(\s*\([^,]*\)\s*,[^)]*)/try_umount(\1)/g' "$CORE_HOOK"
    fi
fi

echo "=== Kernel 4.9 compatibility patches applied ==="
