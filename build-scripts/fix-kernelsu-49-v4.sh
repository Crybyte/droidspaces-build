#!/bin/bash
# KernelSU-Next kernel 4.9 compatibility fix - Version 4
# Complete rewrite of try_umount function for kernel 4.9 compatibility

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

echo "=== KernelSU-Next kernel 4.9 compatibility fix v4 ==="
echo "Directory: $KSU_DIR"

CORE_HOOK="$KSU_DIR/core_hook.c"

if [ ! -f "$CORE_HOOK" ]; then
    echo "ERROR: core_hook.c not found!"
    exit 1
fi

echo "Found core_hook.c"

# Create backup
cp "$CORE_HOOK" "${CORE_HOOK}.bak.v4"

# Check current try_umount function signature
echo "=== Current try_umount function ==="
grep -n "static.*try_umount" "$CORE_HOOK" | head -5 || echo "Function not found"

# Use Python to completely rewrite the try_umount function
# This handles the check_mnt and flags issues in kernel 4.9
python3 << 'PYEOF'
import re
import sys

filepath = "/dev/null"
if len(sys.argv) > 1:
    filepath = sys.argv[1]

# Get KSU_DIR from environment
import os
ksu_dir = os.environ.get('KSU_DIR', '')
if not ksu_dir:
    ksu_dir = sys.argv[1] if len(sys.argv) > 1 else ''
    
filepath = os.path.join(ksu_dir, 'core_hook.c')

if not os.path.exists(filepath):
    print(f"ERROR: File not found: {filepath}")
    sys.exit(1)

with open(filepath, 'r') as f:
    content = f.read()

# Find and replace the try_umount function definition
# The function signature in KernelSU-Next v1.0.7 is:
# static void try_umount(const char *mnt, bool check_mnt, int flags)

# Pattern to match the entire try_umount function
pattern = r'static\s+void\s+try_umount\s*\([^)]+\)\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}'

# Replacement function - kernel 4.9 compatible
replacement = '''static void try_umount(const char *mnt, bool check_mnt_unused, int flags_unused)
{
	/* Kernel 4.9 compatible version - check_mnt and flags not used */
	struct path path;
	int err;
	
	err = kern_path(mnt, 0, &path);
	if (err)
		return;

	if (path.dentry != path.mnt->mnt_root) {
		path_put(&path);
		return;
	}

	/* Skip should_umount check for kernel 4.9 compatibility */
	path_put(&path);

	/* Use umount for kernel 4.9 compatibility (path_umount doesn't exist) */
	err = umount(mnt);
	if (err)
		pr_warn("umount %s failed: %d\\n", mnt, err);
}'''

# Check if the pattern exists
if 'try_umount' in content:
    print("Found try_umount function")
    
    # Try different approaches to replace the function
    
    # Approach 1: Match function with braces counting
    lines = content.split('\n')
    new_lines = []
    i = 0
    in_function = False
    brace_count = 0
    func_start = -1
    
    while i < len(lines):
        line = lines[i]
        
        if not in_function:
            # Look for function definition
            if re.match(r'^static\s+void\s+try_umount', line):
                print(f"Found try_umount at line {i+1}")
                in_function = True
                func_start = i
                brace_count = 0
                # Count braces on this line
                brace_count += line.count('{')
                i += 1
                continue
            new_lines.append(line)
        else:
            # Inside function - count braces
            brace_count += line.count('{')
            brace_count -= line.count('}')
            
            if brace_count <= 0:
                # Function ended, insert replacement
                print(f"Function ended at line {i+1}")
                new_lines.append(replacement)
                in_function = False
            i += 1
            continue
        
        i += 1
    
    if func_start >= 0:
        # Write the modified content
        with open(filepath, 'w') as f:
            f.write('\n'.join(new_lines))
        print("Successfully replaced try_umount function")
    else:
        print("WARNING: Could not find complete try_umount function")
else:
    print("ERROR: try_umount function not found in file")
    sys.exit(1)

PYEOF

if [ $? -ne 0 ]; then
    echo "ERROR: Python fix script failed"
    exit 1
fi

# Also fix ksu_umount_mnt function if it exists - it may use kernel 5.x APIs
if grep -q "ksu_umount_mnt" "$CORE_HOOK" 2>/dev/null; then
    echo "=== Found ksu_umount_mnt - checking if it needs patching ==="
    # Check if ksu_umount_mnt uses path_umount internally
    # If so, we need to replace those calls too
fi

# Fix any remaining path_umount calls in all KSU files
echo "=== Checking for remaining path_umount calls ==="
for file in "$KSU_DIR"/*.c "$KSU_DIR"/*.h; do
    if [ -f "$file" ]; then
        if grep -q "path_umount" "$file" 2>/dev/null; then
            echo "Fixing path_umount in $(basename "$file")"
            # Replace path_umount(path, flags) with umount(path)
            sed -i 's/path_umount\s*(\s*\([^,]*\)\s*,[^)]*)/umount(\1)/g' "$file" || true
        fi
    fi
done

echo "=== Fix complete ==="
exit 0
