#!/bin/bash
# Fix KernelSU-Next v1.0.7 for kernel 4.9 compatibility - VERSION 10
# This script handles ksu_umount_mnt which v9 missed

set -e

KSU_KERNEL_DIR="${1:-$KSU_DIR}"

if [ -z "$KSU_KERNEL_DIR" ] || [ ! -d "$KSU_KERNEL_DIR" ]; then
    echo "ERROR: KernelSU kernel directory not found: $KSU_KERNEL_DIR"
    exit 1
fi

echo "=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fix v10 ==="
echo "Target directory: $KSU_KERNEL_DIR"

CORE_HOOK="$KSU_KERNEL_DIR/core_hook.c"

if [ ! -f "$CORE_HOOK" ]; then
    echo "WARNING: core_hook.c not found at $CORE_HOOK"
    exit 0
fi

# Create backup
cp "$CORE_HOOK" "${CORE_HOOK}.bak.v10"

echo "Applying aggressive kernel 4.9 compatibility patches..."

# Step 1: Handle ksu_umount_mnt calls - replace with umount and remove flags argument
echo "Step 1: Fixing ksu_umount_mnt calls..."
# ksu_umount_mnt(&path, flags) -> umount(mnt) for kernel 4.9
# The function takes a path struct and flags - we need to convert to just the mnt string
perl -i -pe 's/ksu_umount_mnt\s*\(\s*&?path\s*,\s*[^)]+\)/umount(mnt)/g' "$CORE_HOOK"
echo "Fixed ksu_umount_mnt calls"

# Step 2: Find and completely replace the try_umount function definition
echo ""
echo "Step 2: Finding and replacing try_umount function..."

# Get the exact line where try_umount function starts
START_LINE=$(grep -n "^static int try_umount" "$CORE_HOOK" | head -1 | cut -d: -f1 || echo "")

if [ -z "$START_LINE" ]; then
    echo "WARNING: try_umount function not found - may already be patched or have different signature"
else
    echo "Found try_umount function starting at line $START_LINE"
    
    # Find the opening brace line
    OPEN_BRACE_LINE=""
    for i in 0 1 2 3; do
        if sed -n "$((START_LINE+i))p" "$CORE_HOOK" | grep -q "{"; then
            OPEN_BRACE_LINE=$((START_LINE+i))
            break
        fi
    done
    
    if [ -z "$OPEN_BRACE_LINE" ]; then
        echo "ERROR: Could not find opening brace of try_umount function"
    else
        echo "Opening brace at line $OPEN_BRACE_LINE"
        
        # Count braces to find the closing brace
        END_LINE=$(awk -v start="$OPEN_BRACE_LINE" ''
            NR >= start {
                line = $0
                for (i = 1; i <= length(line); i++) {
                    c = substr(line, i, 1)
                    if (c == "{") count++
                    if (c == "}") {
                        count--
                        if (count == 0) {
                            print NR
                            exit
                        }
                    }
                }
            }
        ''' "$CORE_HOOK")
        
        if [ -n "$END_LINE" ]; then
            echo "Function ends at line $END_LINE"
            
            # Show current function
            echo "Current function content:"
            sed -n "${START_LINE},${END_LINE}p" "$CORE_HOOK" || true
            
            # Create the replacement function - kernel 4.9 compatible, NO flags variable
            cat > /tmp/try_umount_replacement.txt << '''REPLACEMENT_EOF'''
static int try_umount(const char *mnt)
{
	struct path path;
	int err = kern_path(mnt, LOOKUP_FOLLOW, &path);
	if (err)
		return err;

	// Kernel 4.9 compatibility: use umount() instead of ksu_umount_mnt()
	err = umount(mnt);

	path_put(&path);
	return err;
}
REPLACEMENT_EOF

            # Build the new file
            head -n $((START_LINE - 1)) "$CORE_HOOK" > /tmp/core_hook_new.c
            cat /tmp/try_umount_replacement.txt >> /tmp/core_hook_new.c
            tail -n +$((END_LINE + 1)) "$CORE_HOOK" >> /tmp/core_hook_new.c
            
            mv /tmp/core_hook_new.c "$CORE_HOOK"
            echo "SUCCESS: Replaced try_umount function (lines $START_LINE-$END_LINE)"
        fi
    fi
fi

# Step 3: Fix try_umount CALLS - they might have 2 or 3 arguments
echo ""
echo "Step 3: Fixing try_umount calls to use single argument..."
# Replace 3-argument calls: try_umount(path, check_mnt, flags) -> try_umount(path)
perl -i -pe '''s/try_umount\s*\(\s*([^,]+)\s*,\s*[^,]+\s*,\s*[^)]+\s*\)/try_umount($1)/g''' "$CORE_HOOK"
# Replace 2-argument calls: try_umount(path, flags) -> try_umount(path)
perl -i -pe '''s/try_umount\s*\(\s*([^,]+)\s*,\s*[^)]+\s*\)/try_umount($1)/g''' "$CORE_HOOK"
echo "Fixed try_umount calls"

# Step 4: Fix path_umount calls (if any remain)
echo ""
echo "Step 4: Fixing path_umount calls..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        perl -i -pe '''s/path_umount\s*\(\s*([^,]+)\s*,[^)]+\)/umount($1)/g''' "$file"
    fi
done
echo "Fixed path_umount calls"

# Step 5: Fix KERNEL_VERSION calls
echo ""
echo "Step 5: Fixing KERNEL_VERSION calls..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        perl -i -pe '''s/KERNEL_VERSION\s*\(\s*([0-9]+)\s*,\s*([0-9]+)\s*\)/KERNEL_VERSION($1, $2, 0)/g''' "$file"
    fi
done
echo "Fixed KERNEL_VERSION calls"

# Step 6: Remove any remaining check_mnt or flags references
echo ""
echo "Step 6: Removing check_mnt and flags references..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        perl -i -pe '''s/check_mnt/0/g''' "$file"
    fi
done
echo "Removed check_mnt references"

# Step 7: Verify fixes
echo ""
echo "Step 7: Verifying fixes..."

echo "Checking for ksu_umount_mnt..."
if grep -n "ksu_umount_mnt" "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h 2>/dev/null; then
    echo "WARNING: ksu_umount_mnt still found!"
else
    echo "OK: No ksu_umount_mnt references"
fi

echo "Checking for path_umount..."
if grep -n "path_umount" "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h 2>/dev/null; then
    echo "WARNING: path_umount still found!"
else
    echo "OK: No path_umount references"
fi

echo "Checking try_umount function signature..."
grep -A 1 "^static int try_umount" "$CORE_HOOK" | head -2

echo ""
echo "=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fix v10 complete ==="
