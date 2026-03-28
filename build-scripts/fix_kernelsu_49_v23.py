#!/usr/bin/env python3
"""
KernelSU-Next v1.0.7 kernel 4.9 compatibility fixer v23
Addresses: 'flags' undeclared in try_umount function

The issue: KernelSU-Next v1.0.7 uses ksu_umount_mnt(&path, flags) but in kernel 4.9
the try_umount function doesn't have a flags parameter, so 'flags' is undeclared.

This fixer:
1. Replaces ksu_umount_mnt(&path, flags) with ksu_umount_mnt(&path, 0)
2. Handles the try_umount function to ensure compatibility
"""

import sys
import re
import os

def fix_core_hook(filepath):
    """Fix core_hook.c for kernel 4.9 compatibility"""

    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return False

    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content
    fixes_applied = []

    # Fix 1: Replace ksu_umount_mnt(&path, flags) with ksu_umount_mnt(&path, 0)
    # This is the critical fix for the 'flags undeclared' error
    pattern1 = r'ksu_umount_mnt\s*\(\s*&path\s*,\s*flags\s*\)'
    replacement1 = 'ksu_umount_mnt(&path, 0)'
    new_content, count1 = re.subn(pattern1, replacement1, content)
    if count1 > 0:
        fixes_applied.append(f"Fixed {count1} ksu_umount_mnt(&path, flags) calls -> ksu_umount_mnt(&path, 0)")
        content = new_content

    # Fix 2: Replace any remaining bare 'flags' references in try_umount with 0
    # Only match 'flags' that are standalone (not part of other words)
    # Look for patterns like "some_func(..., flags)" or "var = flags"
    pattern2 = r'(?<![a-zA-Z0-9_])flags(?![a-zA-Z0-9_])'

    # Find all occurrences of 'flags' in the content
    flags_matches = list(re.finditer(pattern2, content))

    if flags_matches:
        # We need to be careful - only replace flags that are in the context of function calls
        # within the try_umount function or ksu_umount_mnt calls
        # Replace flags with 0 in function call contexts
        new_content = content

        # Pattern: func_name(..., flags, ...) or func_name(..., flags)
        pattern_func = r'(\w+\s*\([^)]*)\bflags\b([^)]*\))'

        def replace_flags_in_call(match):
            before = match.group(1)
            after = match.group(2)
            return f'{before}0{after}'

        new_content, count2 = re.subn(pattern_func, replace_flags_in_call, new_content)
        if count2 > 0:
            fixes_applied.append(f"Fixed {count2} flags parameters in function calls -> 0")
            content = new_content

    # Fix 3: If try_umount still has a 'flags' parameter in its signature, remove it
    # Pattern: static int try_umount(struct path *path, unsigned int flags)
    pattern3 = r'(static\s+int\s+try_umount\s*\(\s*struct\s+path\s*\*\s*\w+\s*,)\s*unsigned\s+int\s+flags\s*\)'
    replacement3 = r'\1)'
    new_content, count3 = re.subn(pattern3, replacement3, content)
    if count3 > 0:
        fixes_applied.append(f"Removed 'unsigned int flags' from try_umount signature ({count3}x)")
        content = new_content

    # Fix 4: Also try simpler pattern for flags parameter removal
    pattern4 = r'int\s+flags\s*[=;]'
    new_content, count4 = re.subn(pattern4, 'int ksu_flags = 0;', content)
    if count4 > 0:
        fixes_applied.append(f"Replaced 'int flags' declarations ({count4}x)")
        content = new_content

    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✓ Fixed {filepath}")
        for fix in fixes_applied:
            print(f"  - {fix}")
        return True
    else:
        print(f"No changes needed for {filepath}")
        return False


def main():
    if len(sys.argv) > 1:
        ksu_dir = sys.argv[1]
    else:
        ksu_dir = os.environ.get('KSU_DIR', 'KernelSU/kernel')

    core_hook = os.path.join(ksu_dir, 'core_hook.c')

    print(f"=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fixer v23 ===")
    print(f"Target: {core_hook}")
    print()

    success = fix_core_hook(core_hook)

    if success:
        print("\n✓ Fixes applied successfully")
        sys.exit(0)
    else:
        print("\n✗ No fixes applied")
        sys.exit(1)


if __name__ == '__main__':
    main()
