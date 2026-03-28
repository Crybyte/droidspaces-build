#!/bin/bash
# fix-kernelsu-49.sh - KernelSU-Next v1.0.7 kernel 4.9 compatibility fixes
# This script patches KernelSU source files for kernel 4.9 compatibility

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

echo "=== Applying kernel 4.9 compatibility patches to $KSU_KERNEL_DIR ==="

# Fix 1: Replace path_umount(path, flags) with umount(path) in all files
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        # Count occurrences
        COUNT=$(grep -c "path_umount" "$file" 2>/dev/null || echo "0")
        if [ "$COUNT" -gt 0 ]; then
            echo "Patching path_umount in $(basename "$file")..."
            # Replace path_umount(path, anything) with umount(path)
            sed -i 's/path_umount\s*(\s*\([^,]*\)\s*,[^)]*)/umount(\1)/g' "$file"
            # Cleanup any remaining path_umount references
            sed -i 's/path_umount/umount/g' "$file"
        fi
    fi
done

# Fix 2: Replace 2-argument KERNEL_VERSION with 3-argument version
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        # Check for KERNEL_VERSION(x, y) pattern (2 args)
        if grep -q 'KERNEL_VERSION\s*(\s*[0-9]\+\s*,\s*[0-9]\+\s*)' "$file" 2>/dev/null; then
            echo "Patching KERNEL_VERSION in $(basename "$file")..."
            sed -i 's/KERNEL_VERSION\s*(\s*\([0-9]\+\)\s*,\s*\([0-9]\+\)\s*)/KERNEL_VERSION(\1, \2, 0)/g' "$file"
        fi
    fi
done

# Fix 3: CRITICAL - Fix try_umount function definition in core_hook.c
CORE_HOOK="$KSU_KERNEL_DIR/core_hook.c"
if [ -f "$CORE_HOOK" ]; then
    echo "Checking try_umount function in core_hook.c..."
    
    # Check if the 3-parameter version exists
    if grep -q 'static int try_umount(struct path \*path, bool check_mnt' "$CORE_HOOK"; then
        echo "Found 3-parameter try_umount - replacing with kernel 4.9 compatible version..."
        
        # Create the replacement function
        REPLACEMENT='static int try_umount(struct path *path)
{
	int err = 0;
	struct mount *mnt = real_mount(path->mnt);

	if (!should_umount(mnt)) {
		return -EBUSY;
	}

	err = umount(path);
	return err;
}'
        
        # Use awk to replace the function
        awk -v replacement="$REPLACEMENT" '
            /static int try_umount\(struct path \*path, bool check_mnt/ {
                print replacement
                brace_count = 1
                in_function = 1
                next
            }
            in_function {
                if (/\{/) brace_count++
                if (/\}/) brace_count--
                if (brace_count == 0) {
                    in_function = 0
                }
                next
            }
            { print }
        ' "$CORE_HOOK" > "${CORE_HOOK}.tmp"
        
        mv "${CORE_HOOK}.tmp" "$CORE_HOOK"
        echo "Successfully replaced try_umount function"
    else
        echo "3-parameter try_umount not found - may already be patched"
    fi
    
    # Fix 4: Replace any 2-argument try_umount calls with 1 argument
    if grep -q 'try_umount\s*([^,]*,[^)]*)' "$CORE_HOOK"; then
        echo "Patching try_umount calls..."
        sed -i 's/try_umount\s*(\s*\([^,]*\)\s*,[^)]*)/try_umount(\1)/g' "$CORE_HOOK"
    fi
fi

echo "=== Kernel 4.9 compatibility patches applied successfully ==="
