#!/usr/bin/env python3
"""
KernelSU-Next v1.0.7 kernel 4.9 compatibility fixer v26
Addresses: Order-of-operations issue - ensures fixes are applied AFTER pre-patch

This fixer runs AFTER the pre-patched file is copied and handles any remaining
issues by being extremely aggressive with pattern matching.

Key insight: The pre-patched file should already have the fixes, but if the
build still fails with 'flags undeclared', we need to force-fix it.
"""

import sys
import re
import os

def fix_core_hook(filepath):
    """Fix core_hook.c for kernel 4.9 compatibility - v26 force-fix"""

    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return False

    with open(filepath, 'r') as f:
        lines = f.readlines()

    original_content = ''.join(lines)
    fixes_applied = []
    modified = False

    # Read line by line to handle specific line 591 issue
    for i, line in enumerate(lines):
        original_line = line

        # Fix 1: ksu_umount_mnt(&path, flags) -> ksu_umount_mnt(&path)
        # This specifically targets line 591 and any similar lines
        if 'ksu_umount_mnt(&path, flags)' in line:
            line = line.replace('ksu_umount_mnt(&path, flags)', 'ksu_umount_mnt(&path)')
            fixes_applied.append(f"Line {i+1}: Fixed ksu_umount_mnt(&path, flags) -> ksu_umount_mnt(&path)")

        # Fix 2: ksu_umount_mnt(path, flags) -> ksu_umount_mnt(path)
        # Handles variable names other than &path
        elif re.search(r'ksu_umount_mnt\s*\(\s*[^,)]+\s*,\s*flags\s*\)', line):
            line = re.sub(r'ksu_umount_mnt\s*\(\s*([^,)]+)\s*,\s*flags\s*\)', r'ksu_umount_mnt(\1)', line)
            fixes_applied.append(f"Line {i+1}: Fixed ksu_umount_mnt(..., flags) call")

        # Fix 3: try_umount(mnt, check_mnt, flags) -> try_umount(mnt, check_mnt)
        if re.search(r'try_umount\s*\([^,]+,[^,]+,[^)]+\)', line):
            line = re.sub(r'try_umount\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*[^)]+\s*\)', r'try_umount(\1, \2)', line)
            fixes_applied.append(f"Line {i+1}: Fixed 3-arg try_umount call")

        if line != original_line:
            lines[i] = line
            modified = True

    content = ''.join(lines)

    # Fix 4: Function signature replacements (multi-line aware)
    # ksu_umount_mnt(struct path *path, int flags) -> ksu_umount_mnt(struct path *path)
    new_content, count = re.subn(
        r'static\s+int\s+ksu_umount_mnt\s*\(\s*struct\s+path\s*\*\s*\w+\s*,\s*int\s+\w+\s*\)',
        'static int ksu_umount_mnt(struct path *path)',
        content
    )
    if count > 0:
        fixes_applied.append(f"Fixed ksu_umount_mnt function signature ({count})")
        content = new_content
        modified = True

    # Fix 5: try_umount signature with flags
    new_content, count = re.subn(
        r'static\s+void\s+try_umount\s*\(\s*const\s+char\s*\*\s*\w+\s*,\s*bool\s+\w+\s*,\s*int\s+\w+\s*\)',
        'static void try_umount(const char *mnt, bool check_mnt)',
        content
    )
    if count > 0:
        fixes_applied.append(f"Fixed try_umount 3-arg signature ({count})")
        content = new_content
        modified = True

    # Fix 6: path_umount calls
    new_content, count = re.subn(
        r'path_umount\s*\(\s*([^,)]+)\s*,\s*[^)]+\s*\)',
        r'umount(\1)',
        content
    )
    if count > 0:
        fixes_applied.append(f"Fixed {count} path_umount calls")
        content = new_content
        modified = True

    if modified:
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

    print(f"=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fixer v26 ===")
    print(f"Target: {core_hook}")
    print()

    success = fix_core_hook(core_hook)

    if success:
        print("\n✓ Fixes applied successfully")
        sys.exit(0)
    else:
        print("\n✗ No fixes applied")
        sys.exit(0)  # Exit 0 so build continues even if no fixes needed


if __name__ == '__main__':
    main()
