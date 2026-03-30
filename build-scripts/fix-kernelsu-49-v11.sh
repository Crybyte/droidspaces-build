#!/bin/bash
# Fix KernelSU-Next v1.0.7 for kernel 4.9 compatibility - VERSION 11
# This script handles the 'flags undeclared' error more aggressively

set -e

KSU_KERNEL_DIR="${1:-$KSU_DIR}"

if [ -z "$KSU_KERNEL_DIR" ] || [ ! -d "$KSU_KERNEL_DIR" ]; then
    echo "ERROR: KernelSU kernel directory not found: $KSU_KERNEL_DIR"
    exit 1
fi

echo "=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fix v11 ==="
echo "Target directory: $KSU_KERNEL_DIR"

CORE_HOOK="$KSU_KERNEL_DIR/core_hook.c"

if [ ! -f "$CORE_HOOK" ]; then
    echo "WARNING: core_hook.c not found at $CORE_HOOK"
    exit 0
fi

# Create backup
cp "$CORE_HOOK" "${CORE_HOOK}.bak.v11"

echo "Applying aggressive kernel 4.9 compatibility patches..."

# Step 1: First, completely replace the try_umount function BEFORE fixing calls
echo ""
echo "Step 1: Replacing try_umount function entirely..."

# Get the exact line where try_umount function starts
START_LINE=$(grep -n "^static int try_umount" "$CORE_HOOK" | head -1 | cut -d: -f1 || echo "")

if [ -n "$START_LINE" ]; then
    echo "Found try_umount function starting at line $START_LINE"
    
    # Find the opening brace line
    OPEN_BRACE_LINE=""
    for i in 0 1 2 3 4 5; do
        if sed -n "$((START_LINE+i))p" "$CORE_HOOK" | grep -q "{"; then
            OPEN_BRACE_LINE=$((START_LINE+i))
            break
        fi
    done
    
    if [ -n "$OPEN_BRACE_LINE" ]; then
        echo "Opening brace at line $OPEN_BRACE_LINE"
        
        # Find the function end by counting braces
        END_LINE=""
        brace_count=0
        in_function=0
        
        while IFS= read -r line; do
            current_line=$((current_line + 1))
            if [ $current_line -lt $OPEN_BRACE_LINE ]; then
                continue
            fi
            
            if [ $in_function -eq 0 ] && echo "$line" | grep -q "{"; then
                in_function=1
            fi
            
            if [ $in_function -eq 1 ]; then
                # Count braces
                opens=$(echo "$line" | tr -cd '{' | wc -c)
                closes=$(echo "$line" | tr -cd '}' | wc -c)
                brace_count=$((brace_count + opens - closes))
                
                if [ $brace_count -eq 0 ] && [ $current_line -gt $OPEN_BRACE_LINE ]; then
                    END_LINE=$current_line
                    break
                fi
            fi
        done < "$CORE_HOOK"
        
        current_line=0
        
        if [ -n "$END_LINE" ]; then
            echo "Function ends at line $END_LINE"
            echo "Replacing lines $START_LINE-$END_LINE with kernel 4.9 compatible version..."
            
            # Build the new file with the replacement function
            head -n $((START_LINE - 1)) "$CORE_HOOK" > /tmp/core_hook_new.c
            
            # Insert the new function - NO flags variable at all
            cat >> /tmp/core_hook_new.c << 'EOF'
static int try_umount(const char *mnt)
{
	struct path path;
	int err = kern_path(mnt, LOOKUP_FOLLOW, &path);
	if (err)
		return err;

	// Kernel 4.9 compatibility: umount doesn't take flags
	// Just use the mnt path directly
	path_put(&path);
	err = umount(mnt);

	return err;
}
EOF
            
            tail -n +$((END_LINE + 1)) "$CORE_HOOK" >> /tmp/core_hook_new.c
            mv /tmp/core_hook_new.c "$CORE_HOOK"
            echo "SUCCESS: Replaced try_umount function"
        fi
    fi
else
    echo "WARNING: try_umount function not found"
fi

# Step 2: Remove any remaining ksu_umount_mnt calls (they shouldn't exist after function replacement, but just in case)
echo ""
echo "Step 2: Removing any remaining ksu_umount_mnt calls..."
perl -i -pe 's/ksu_umount_mnt\s*\([^)]+\);/umount(mnt);/g' "$CORE_HOOK"
perl -i -pe 's/ksu_umount_mnt\s*\([^)]+\)/umount(mnt)/g' "$CORE_HOOK"

# Step 3: Fix try_umount calls to ensure they only have one argument
echo ""
echo "Step 3: Fixing try_umount calls..."
# Replace multi-argument calls with single argument
perl -i -pe 's/try_umount\s*\(\s*([^,\)]+)\s*,[^\)]+\)/try_umount($1)/g' "$CORE_HOOK"

# Step 4: Fix path_umount calls in all files
echo ""
echo "Step 4: Fixing path_umount calls in all KernelSU files..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        perl -i -pe 's/path_umount\s*\(\s*([^,]+)\s*,[^\)]+\)/umount($1)/g' "$file"
    fi
done

# Step 5: Fix KERNEL_VERSION calls
echo ""
echo "Step 5: Fixing KERNEL_VERSION calls..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        perl -i -pe 's/KERNEL_VERSION\s*\(\s*([0-9]+)\s*,\s*([0-9]+)\s*\)/KERNEL_VERSION($1, $2, 0)/g' "$file"
    fi
done

# Step 6: Replace check_mnt with 0
echo ""
echo "Step 6: Replacing check_mnt with 0..."
for file in "$KSU_KERNEL_DIR"/*.c "$KSU_KERNEL_DIR"/*.h; do
    if [ -f "$file" ]; then
        perl -i -pe 's/\bcheck_mnt\b/0/g' "$file"
    fi
done

# Step 7: Remove any 'int flags' or similar declarations that might be unused now
echo ""
echo "Step 7: Cleaning up unused flags declarations..."
perl -i -pe 's/^\s*int\s+flags\s*;\s*$//g' "$CORE_HOOK"
perl -i -pe 's/^\s*unsigned\s+int\s+flags\s*;\s*$//g' "$CORE_HOOK"

echo ""
echo "=== Kernel 4.9 compatibility patches applied successfully (v11) ==="
