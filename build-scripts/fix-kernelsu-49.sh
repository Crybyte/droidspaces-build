#!/bin/bash
# Fix KernelSU-Next v1.0.7 for kernel 4.9 compatibility
# This script patches the try_umount function definition which uses kernel 5.x symbols

set -e

KSU_KERNEL_DIR="$1"

if [ -z "$KSU_KERNEL_DIR" ] || [ ! -d "$KSU_KERNEL_DIR" ]; then
    echo "ERROR: KernelSU kernel directory not found: $KSU_KERNEL_DIR"
    exit 1
fi

echo "=== Fixing KernelSU-Next for kernel 4.9 compatibility ==="
echo "Target directory: $KSU_KERNEL_DIR"

# The try_umount function in core_hook.c uses check_mnt() and flags variable
# which don't exist in kernel 4.9. We need to completely rewrite this function.

CORE_HOOK="$KSU_KERNEL_DIR/core_hook.c"

if [ ! -f "$CORE_HOOK" ]; then
    echo "WARNING: core_hook.c not found at $CORE_HOOK"
    exit 0
fi

# Create backup
cp "$CORE_HOOK" "${CORE_HOOK}.bak"

echo "Patching try_umount function in core_hook.c..."

# Use Python for complex multi-line replacement
python3 << 'PYTHON_SCRIPT'
import re
import sys

filepath = "'''+$CORE_HOOK+'''"

with open(filepath, 'r') as f:
    content = f.read()

# Pattern to match the try_umount function (including its body)
# This matches from "static int try_umount" to the closing brace
old_function_pattern = r'static int try_umount\s*\([^)]+\)\s*\{[^}]*\{[^}]*\}[^}]*\}'

# New implementation for kernel 4.9
# Uses umount() instead of path_umount() and removes check_mnt usage
new_function = '''static int try_umount(const char *mnt, int flags)
{
	struct path path;
	int err = kern_path(mnt, LOOKUP_FOLLOW, &path);
	if (err)
		return err;
	
	// For kernel 4.9 compatibility, use umount directly
	// instead of path_umount which doesn't exist
	if (path.dentry && path.dentry->d_sb && path.dentry->d_sb->s_root)
		err = umount(mnt);
	else
		err = -EINVAL;
	
	path_put(&path);
	return err;
}'''

# Search for try_umount function
try_umount_match = re.search(old_function_pattern, content, re.DOTALL)

if try_umount_match:
    print(f"Found try_umount function at position {try_umount_match.start()}")
    old_func = try_umount_match.group(0)
    print("Old function:")
    print(old_func[:200] + "...")
    
    # Replace with new implementation
    content = content[:try_umount_match.start()] + new_function + content[try_umount_match.end():]
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print("SUCCESS: try_umount function replaced with kernel 4.9 compatible version")
else:
    # Try simpler pattern - just find the function declaration
    simple_pattern = r'static int try_umount\s*\([^)]*\)'
    match = re.search(simple_pattern, content)
    if match:
        print(f"Found try_umount declaration at position {match.start()}")
        print("Function found but pattern matching failed - manual inspection needed")
        print("Declaration:", match.group(0))
        sys.exit(1)
    else:
        print("try_umount function not found - may already be patched or not present")
        sys.exit(0)
PYTHON_SCRIPT

# Now patch any remaining path_umount calls
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        # Replace path_umount with umount
        perl -i -pe 's/path_umount\s*\(\s*([^,]+)\s*,[^)]+\)/umount($1)/g' "$file"
    fi
done

# Verify no path_umount remains
REMAINING=$(grep -c "path_umount" "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h 2>/dev/null | wc -l || echo "0")
if [ "$REMAINING" -gt 0 ]; then
    echo "WARNING: $REMAINING path_umount references still found"
    grep -n "path_umount" "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h 2>/dev/null | head -20
fi

echo "=== KernelSU-Next kernel 4.9 compatibility patching complete ==="
