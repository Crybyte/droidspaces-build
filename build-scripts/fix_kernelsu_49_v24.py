#!/usr/bin/env python3
"""
KernelSU-Next v1.0.7 kernel 4.9 compatibility fixer v24
Addresses: 'flags' undeclared in try_umount function at line 591

The issue: KernelSU-Next v1.0.7 uses ksu_umount_mnt(&path, flags) but in kernel 4.9
the try_umount function doesn't have a flags variable, so 'flags' is undeclared.

The actual code structure in v1.0.7:
- Line ~563: static int ksu_umount_mnt(struct path *path, int flags)
- Line ~591: err = ksu_umount_mnt(&path, flags);  <-- ERROR: flags undeclared

This fixer:
1. Replaces the ksu_umount_mnt function signature to remove flags parameter
2. Replaces ksu_umount_mnt(&path, flags) calls with ksu_umount_mnt(&path, 0)
3. Replaces the function body to not use flags
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

    # Fix 1: Replace ksu_umount_mnt function definition
    # From: static int ksu_umount_mnt(struct path *path, int flags)
    # To: static int ksu_umount_mnt(struct path *path)
    pattern1 = r'static\s+int\s+ksu_umount_mnt\s*\(\s*struct\s+path\s*\*\s*path\s*,\s*int\s+flags\s*\)'
    replacement1 = 'static int ksu_umount_mnt(struct path *path)'
    new_content, count1 = re.subn(pattern1, replacement1, content)
    if count1 > 0:
        fixes_applied.append(f"Fixed ksu_umount_mnt function definition (removed flags parameter)")
        content = new_content

    # Fix 2: Replace ksu_umount_mnt(&path, flags) with ksu_umount_mnt(&path, 0)
    # This handles the call at line 591
    pattern2 = r'ksu_umount_mnt\s*\(\s*&path\s*,\s*flags\s*\)'
    replacement2 = 'ksu_umount_mnt(&path, 0)'
    new_content, count2 = re.subn(pattern2, replacement2, content)
    if count2 > 0:
        fixes_applied.append(f"Fixed {count2} ksu_umount_mnt(&path, flags) calls -> ksu_umount_mnt(&path, 0)")
        content = new_content

    # Fix 3: Replace any other ksu_umount_mnt calls with second argument
    # Pattern: ksu_umount_mnt(anything, flags) -> ksu_umount_mnt(anything, 0)
    pattern3 = r'ksu_umount_mnt\s*\(\s*([^,]+)\s*,\s*flags\s*\)'
    replacement3 = r'ksu_umount_mnt(\1, 0)'
    new_content, count3 = re.subn(pattern3, replacement3, content)
    if count3 > 0:
        fixes_applied.append(f"Fixed {count3} other ksu_umount_mnt(..., flags) calls")
        content = new_content

    # Fix 4: Replace flags usage inside ksu_umount_mnt function body
    # Look for patterns like "umount(path, flags)" inside the function
    # We need to be careful to only replace within the function
    pattern4 = r'(ksu_umount_mnt\s*\(\s*[^)]+\)\s*\{[^}]*?)umount\s*\(\s*([^,]+)\s*,\s*flags\s*\)'
    replacement4 = r'\1umount(\2)'
    new_content, count4 = re.subn(pattern4, replacement4, content, flags=re.DOTALL)
    if count4 > 0:
        fixes_applied.append(f"Fixed umount calls inside ksu_umount_mnt function")
        content = new_content

    # Fix 5: Alternative - handle the specific pattern where umount is called with path and flags
    # This is for kernel 4.9 compatibility - path_umount doesn't exist, use umount
    pattern5 = r'path_umount\s*\(\s*([^,]+)\s*,\s*[^)]+\s*\)'
    replacement5 = r'umount(\1)'
    new_content, count5 = re.subn(pattern5, replacement5, content)
    if count5 > 0:
        fixes_applied.append(f"Fixed {count5} path_umount calls -> umount")
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

    print(f"=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fixer v24 ===")
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
