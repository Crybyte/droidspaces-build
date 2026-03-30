#!/bin/bash
# Fix KernelSU-Next v1.0.7 for kernel 4.9 compatibility - VERSION 12
# SIMPLIFIED approach: Use perl to completely rewrite the try_umount function

set -e

KSU_KERNEL_DIR="${1:-$KSU_DIR}"

if [ -z "$KSU_KERNEL_DIR" ] || [ ! -d "$KSU_KERNEL_DIR" ]; then
    echo "ERROR: KernelSU kernel directory not found: $KSU_KERNEL_DIR"
    exit 1
fi

echo "=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fix v12 ==="
echo "Target directory: $KSU_KERNEL_DIR"

CORE_HOOK="$KSU_KERNEL_DIR/core_hook.c"

if [ ! -f "$CORE_HOOK" ]; then
    echo "WARNING: core_hook.c not found at $CORE_HOOK"
    exit 0
fi

# Create backup
cp "$CORE_HOOK" "${CORE_HOOK}.bak.v12"

echo "Applying aggressive kernel 4.9 compatibility patches..."

# Step 1: Use perl to slurp the entire file and replace the try_umount function
echo ""
echo "Step 1: Completely replacing try_umount function with perl..."

perl -i -0777 -pe '
# Match the try_umount function and replace it entirely
# Pattern: static int try_umount ... { ... }
s/static int try_umount\s*\([^)]*\)\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/static int try_umount(const char *mnt)
{
\tstruct path path;
\tint err = kern_path(mnt, LOOKUP_FOLLOW, \&path);
\tif (err)
\t\treturn err;

\t// Kernel 4.9 compatibility: use umount directly
\tpath_put(\&path);
\terr = umount(mnt);

\treturn err;
}/s;
' "$CORE_HOOK"

# Check if replacement worked
if grep -q "static int try_umount(const char \*mnt)" "$CORE_HOOK"; then
    echo "SUCCESS: try_umount function signature updated"
else
    echo "WARNING: try_umount function signature may not have been updated"
    echo "Current signature:"
    grep -n "static int try_umount" "$CORE_HOOK" | head -3
fi

# Step 2: Remove ANY remaining lines that reference 'flags' in the try_umount function area
echo ""
echo "Step 2: Removing all flags references in try_umount function..."

# Find the try_umount function and remove any lines with 'flags' in it
perl -i -pe '
    if (/^static int try_umount/) { $in_func = 1; }
    if ($in_func) {
        # Remove lines that declare or use flags
        if (/\bflags\b/ && !/^[\s]*\//) { $_ = ""; }
        # Track braces to know when function ends
        $opens = tr/{//;
        $closes = tr/}//;
        $brace_count += $opens - $closes;
        if ($brace_count == 0 && $opens > 0) { $in_func = 0; }
    }
' "$CORE_HOOK"

# Step 3: Replace any remaining ksu_umount_mnt calls
echo ""
echo "Step 3: Replacing ksu_umount_mnt calls..."
perl -i -pe 's/ksu_umount_mnt\s*\([^)]+\)/umount(mnt)/g' "$CORE_HOOK"

# Step 4: Fix try_umount calls to have single argument
echo ""
echo "Step 4: Fixing try_umount calls..."
perl -i -pe 's/try_umount\s*\(\s*([^,\)]+)\s*,[^\)]+\)/try_umount($1)/g' "$CORE_HOOK"

# Step 5: Fix path_umount calls in all files
echo ""
echo "Step 5: Fixing path_umount calls..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        perl -i -pe 's/path_umount\s*\(\s*([^,]+)\s*,[^\)]+\)/umount($1)/g' "$file"
    fi
done

# Step 6: Fix KERNEL_VERSION calls
echo ""
echo "Step 6: Fixing KERNEL_VERSION calls..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        perl -i -pe 's/KERNEL_VERSION\s*\(\s*([0-9]+)\s*,\s*([0-9]+)\s*\)/KERNEL_VERSION($1, $2, 0)/g' "$file"
    fi
done

# Step 7: Replace check_mnt with 0
echo ""
echo "Step 7: Replacing check_mnt..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        perl -i -pe 's/\bcheck_mnt\b/0/g' "$file"
    fi
done

echo ""
echo "=== Verifying fixes ==="

# Check for remaining issues
echo "Checking for 'flags' in try_umount..."
START_LINE=$(grep -n "^static int try_umount" "$CORE_HOOK" | head -1 | cut -d: -f1 || echo "")
if [ -n "$START_LINE" ]; then
    # Get function end line roughly (find next function or 50 lines)
    END_LINE=$((START_LINE + 50))
    if grep -n "flags" "$CORE_HOOK" | awk -F: -v s="$START_LINE" -v e="$END_LINE" '$1 >= s && $1 <= e {print}' | grep -v "//"; then
        echo "WARNING: 'flags' still found in try_umount function!"
    else
        echo "OK: No 'flags' references in try_umount function"
    fi
fi

echo "Checking for ksu_umount_mnt..."
if grep -q "ksu_umount_mnt" "$CORE_HOOK"; then
    echo "WARNING: ksu_umount_mnt still found!"
    grep -n "ksu_umount_mnt" "$CORE_HOOK"
else
    echo "OK: No ksu_umount_mnt references"
fi

echo "Checking for path_umount..."
if grep -q "path_umount" "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h 2>/dev/null; then
    echo "WARNING: path_umount still found!"
else
    echo "OK: No path_umount references"
fi

echo ""
echo "=== Kernel 4.9 compatibility patches applied (v12) ==="
