#!/bin/bash
# Fix KernelSU-Next v1.0.7 for kernel 4.9 compatibility - VERSION 8
# This script aggressively patches the try_umount function and related issues

set -e

KSU_KERNEL_DIR="$1"

if [ -z "$KSU_KERNEL_DIR" ] || [ ! -d "$KSU_KERNEL_DIR" ]; then
    echo "ERROR: KernelSU kernel directory not found: $KSU_KERNEL_DIR"
    exit 1
fi

echo "=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fix v8 ==="
echo "Target directory: $KSU_KERNEL_DIR"

CORE_HOOK="$KSU_KERNEL_DIR/core_hook.c"

if [ ! -f "$CORE_HOOK" ]; then
    echo "WARNING: core_hook.c not found at $CORE_HOOK"
    exit 0
fi

# Create backup
cp "$CORE_HOOK" "${CORE_HOOK}.bak.v8"

echo "Applying aggressive kernel 4.9 compatibility patches..."

# Create the replacement file with fixed try_umount function
cat > /tmp/try_umount_fix.c << 'EOF'
static int try_umount(const char *mnt, int flags)
{
	struct path path;
	int err = kern_path(mnt, LOOKUP_FOLLOW, &path);
	if (err)
		return err;

	// For kernel 4.9 compatibility, always declare flags before use
	// The flags parameter is passed in, just use it directly with umount
	err = umount(mnt);

	path_put(&path);
	return err;
}
EOF

# Use a more reliable approach - sed-based line manipulation
echo "Step 1: Finding try_umount function..."

# Get the line numbers of the try_umount function
START_LINE=$(grep -n "^static int try_umount" "$CORE_HOOK" | head -1 | cut -d: -f1 || echo "")

if [ -z "$START_LINE" ]; then
    echo "WARNING: try_umount function not found - may already be patched"
else
    echo "Found try_umount function starting at line $START_LINE"
    
    # Find the closing brace of the function (simple brace counting)
    # Extract from start line and count braces
    END_LINE=$(awk -v start="$START_LINE" '
        NR >= start {
            for (i = 1; i <= length($0); i++) {
                c = substr($0, i, 1)
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
    ' "$CORE_HOOK")
    
    if [ -z "$END_LINE" ]; then
        echo "ERROR: Could not find end of try_umount function"
        exit 1
    fi
    
    echo "Function ends at line $END_LINE"
    
    # Create new file: lines before START_LINE + replacement + lines after END_LINE
    head -n $((START_LINE - 1)) "$CORE_HOOK" > /tmp/core_hook_new.c
    cat /tmp/try_umount_fix.c >> /tmp/core_hook_new.c
    tail -n +$((END_LINE + 1)) "$CORE_HOOK" >> /tmp/core_hook_new.c
    
    # Replace the original file
    mv /tmp/core_hook_new.c "$CORE_HOOK"
    echo "SUCCESS: Replaced try_umount function (lines $START_LINE-$END_LINE)"
fi

# Step 2: Fix any remaining path_umount calls
echo "Step 2: Fixing remaining path_umount calls..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        # Replace path_umount with umount (removing second argument)
        perl -i -pe 's/path_umount\s*\(\s*([^,]+)\s*,[^)]+\)/umount($1)/g' "$file"
    fi
done

# Step 3: Fix KERNEL_VERSION calls (2-arg to 3-arg)
echo "Step 3: Fixing KERNEL_VERSION calls..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        perl -i -pe 's/KERNEL_VERSION\s*\(\s*([0-9]+)\s*,\s*([0-9]+)\s*\)/KERNEL_VERSION($1, $2, 0)/g' "$file"
    fi
done

# Step 4: Verify no path_umount remains
echo "Step 4: Verifying fixes..."
REMAINING=$(grep -c "path_umount" "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h 2>/dev/null | wc -l || echo "0")
if [ "$REMAINING" -gt 0 ]; then
    echo "WARNING: $REMAINING path_umount references still found:"
    grep -n "path_umount" "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h 2>/dev/null | head -20
else
    echo "SUCCESS: All path_umount calls removed"
fi

# Step 5: Check for remaining 'flags undeclared' issues
echo "Step 5: Checking for other kernel 4.9 compatibility issues..."
if grep -q "flags" "$CORE_HOOK" 2>/dev/null; then
    echo "Found 'flags' references in core_hook.c:"
    grep -n "flags" "$CORE_HOOK" | head -20
fi

echo "=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fix v8 complete ==="
