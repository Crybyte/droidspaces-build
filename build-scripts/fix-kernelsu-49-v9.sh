#!/bin/bash
# Fix KernelSU-Next v1.0.7 for kernel 4.9 compatibility - VERSION 9
# This script uses a completely different approach - rewriting the entire file section

set -e

KSU_KERNEL_DIR="${1:-$KSU_DIR}"

if [ -z "$KSU_KERNEL_DIR" ] || [ ! -d "$KSU_KERNEL_DIR" ]; then
    echo "ERROR: KernelSU kernel directory not found: $KSU_KERNEL_DIR"
    exit 1
fi

echo "=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fix v9 ==="
echo "Target directory: $KSU_KERNEL_DIR"

CORE_HOOK="$KSU_KERNEL_DIR/core_hook.c"

if [ ! -f "$CORE_HOOK" ]; then
    echo "WARNING: core_hook.c not found at $CORE_HOOK"
    exit 0
fi

# Create backup
cp "$CORE_HOOK" "${CORE_HOOK}.bak.v9"

echo "Applying aggressive kernel 4.9 compatibility patches..."

# Step 1: Find and completely replace the try_umount function definition
echo "Step 1: Finding try_umount function with line numbers..."

# Get the exact line where try_umount function starts
START_LINE=$(grep -n "^static int try_umount" "$CORE_HOOK" | head -1 | cut -d: -f1 || echo "")

if [ -z "$START_LINE" ]; then
    echo "WARNING: try_umount function not found - may already be patched or have different signature"
    # List all functions in the file to debug
    echo "Functions found in core_hook.c:"
    grep "^static" "$CORE_HOOK" | head -20 || true
else
    echo "Found try_umount function starting at line $START_LINE"
    
    # Show the context around the function
    echo "Context around line $START_LINE:"
    sed -n "$((START_LINE-2)),$((START_LINE+10))p" "$CORE_HOOK" || true
    
    # Find where the function ends by counting braces from START_LINE
    # We'll use a more robust approach - look for the pattern of the next function
    # or end of file
    
    # First, find the line with the opening brace (should be START_LINE or START_LINE+1)
    OPEN_BRACE_LINE=""
    for i in 0 1 2 3; do
        if sed -n "$((START_LINE+i))p" "$CORE_HOOK" | grep -q "{"; then
            OPEN_BRACE_LINE=$((START_LINE+i))
            break
        fi
    done
    
    if [ -z "$OPEN_BRACE_LINE" ]; then
        echo "ERROR: Could not find opening brace of try_umount function"
        exit 1
    fi
    
    echo "Opening brace at line $OPEN_BRACE_LINE"
    
    # Now count braces to find the closing brace
    # Start from OPEN_BRACE_LINE, count { and }, when count reaches 0 we found the end
    END_LINE=$(awk -v start="$OPEN_BRACE_LINE" '
        NR >= start {
            line = $0
            # Count braces in this line
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
    ' "$CORE_HOOK")
    
    if [ -z "$END_LINE" ]; then
        echo "ERROR: Could not find end of try_umount function"
        exit 1
    fi
    
    echo "Function ends at line $END_LINE"
    
    # Show what we're about to replace
    echo "Current function content:"
    sed -n "${START_LINE},${END_LINE}p" "$CORE_HOOK" || true
    
    # Create the replacement function - kernel 4.9 compatible
    # The key issue: kernel 4.9's umount() doesn't take flags parameter
    # We completely remove the flags parameter and any references to it
    cat > /tmp/try_umount_replacement.txt << 'REPLACEMENT_EOF'
static int try_umount(const char *mnt)
{
	struct path path;
	int err = kern_path(mnt, LOOKUP_FOLLOW, &path);
	if (err)
		return err;

	// Kernel 4.9 compatibility: umount() only takes path, no flags
	err = umount(mnt);

	path_put(&path);
	return err;
}
REPLACEMENT_EOF

    # Build the new file
    echo "Building new file..."
    
    # Part 1: Everything before the function
    head -n $((START_LINE - 1)) "$CORE_HOOK" > /tmp/core_hook_new.c
    
    # Part 2: The replacement function
    cat /tmp/try_umount_replacement.txt >> /tmp/core_hook_new.c
    
    # Part 3: Everything after the function
    tail -n +$((END_LINE + 1)) "$CORE_HOOK" >> /tmp/core_hook_new.c
    
    # Replace the original
    mv /tmp/core_hook_new.c "$CORE_HOOK"
    
    echo "SUCCESS: Replaced try_umount function (lines $START_LINE-$END_LINE)"
    
    # Verify the replacement
    echo "New function content:"
    NEW_START=$(grep -n "^static int try_umount" "$CORE_HOOK" | head -1 | cut -d: -f1 || echo "")
    if [ -n "$NEW_START" ]; then
        sed -n "${NEW_START},$((NEW_START+10))p" "$CORE_HOOK" || true
    fi
fi

# Step 2: Fix try_umount CALLS - they might have 2 or 3 arguments
# After our function signature change, calls with 2+ args will fail
echo ""
echo "Step 2: Fixing try_umount calls to use single argument..."

# Replace 3-argument calls: try_umount(path, check_mnt, flags) -> try_umount(path)
perl -i -pe 's/try_umount\s*\(\s*([^,]+)\s*,\s*[^,]+\s*,\s*[^)]+\s*\)/try_umount($1)/g' "$CORE_HOOK"

# Replace 2-argument calls: try_umount(path, flags) -> try_umount(path)
perl -i -pe 's/try_umount\s*\(\s*([^,]+)\s*,\s*[^)]+\s*\)/try_umount($1)/g' "$CORE_HOOK"

echo "Fixed try_umount calls"

# Step 3: Fix any remaining path_umount calls
echo ""
echo "Step 3: Fixing path_umount calls..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        # Replace path_umount(path, flags) with umount(path) for kernel 4.9
        perl -i -pe 's/path_umount\s*\(\s*([^,]+)\s*,[^)]+\)/umount($1)/g' "$file"
        # Also handle path_umount(path, 0) and similar
        perl -i -pe 's/path_umount\s*\(\s*([^,]+)\s*,\s*[^)]+\)/umount($1)/g' "$file"
    fi
done
echo "Fixed path_umount calls"

# Step 4: Fix KERNEL_VERSION calls (2-arg to 3-arg)
echo ""
echo "Step 4: Fixing KERNEL_VERSION calls..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        perl -i -pe 's/KERNEL_VERSION\s*\(\s*([0-9]+)\s*,\s*([0-9]+)\s*\)/KERNEL_VERSION($1, $2, 0)/g' "$file"
    fi
done
echo "Fixed KERNEL_VERSION calls"

# Step 5: Remove any remaining check_mnt references
echo ""
echo "Step 5: Removing check_mnt references..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        # Replace check_mnt with 0/false
        perl -i -pe 's/\bcheck_mnt\b/0/g' "$file"
    fi
done
echo "Removed check_mnt references"

# Step 6: Verify no problematic patterns remain
echo ""
echo "Step 6: Verifying fixes..."

echo "Checking for path_umount..."
if grep -n "path_umount" "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h 2>/dev/null; then
    echo "WARNING: path_umount still found!"
else
    echo "OK: No path_umount references"
fi

echo "Checking for check_mnt..."
if grep -n "check_mnt" "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h 2>/dev/null; then
    echo "WARNING: check_mnt still found!"
else
    echo "OK: No check_mnt references"
fi

echo "Checking try_umount function signature..."
grep -A 1 "^static int try_umount" "$CORE_HOOK" | head -2

echo ""
echo "=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fix v9 complete ==="
