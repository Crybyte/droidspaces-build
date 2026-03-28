#!/usr/bin/env python3
"""
KernelSU-Next kernel 4.9 compatibility fix script v33
Fixes the ksu_umount_mnt function signature mismatch

Issue: The function is declared with 2 args at line 563 but called with 1 arg at line 591
Fix: Change function declaration to accept only 1 arg (struct path *)
"""

import sys
import os
import re

def fix_core_hook_file(filepath):
    """Fix the ksu_umount_mnt function signature and call in core_hook.c"""

    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return False

    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content
    changes = []

    # Fix 1: Change function declaration from 'ksu_umount_mnt(struct path *path, int flags)'
    # to 'ksu_umount_mnt(struct path *path)'
    pattern1 = r'static int\s+ksu_umount_mnt\s*\(\s*struct path\s*\*\s*path\s*,\s*int\s+flags\s*\)'
    replacement1 = 'static int ksu_umount_mnt(struct path *path)'

    if re.search(pattern1, content):
        content = re.sub(pattern1, replacement1, content)
        changes.append("Fixed function declaration (removed flags parameter)")

    # Fix 2: Also fix alternate format with different spacing
    pattern1b = r'static int\s+ksu_umount_mnt\s*\(\s*struct path\s*\*\s*path,\s*int\s+flags\s*\)'
    if re.search(pattern1b, content):
        content = re.sub(pattern1b, replacement1, content)
        changes.append("Fixed function declaration (alt pattern)")

    # Fix 3: Remove 'int flags' parameter declaration from function signature
    # Pattern: function definition line followed by opening brace
    pattern2 = r'(static int ksu_umount_mnt\(struct path \*path\))\s*\{([^}]*int flags;[^}]*\{)'

    # Fix 4: Fix any call sites that still pass 2 arguments
    # ksu_umount_mnt(&path, flags) -> ksu_umount_mnt(&path)
    pattern3 = r'ksu_umount_mnt\s*\(\s*&path\s*,\s*[^)]+\)'
    replacement3 = 'ksu_umount_mnt(&path)'

    if re.search(pattern3, content):
        content = re.sub(pattern3, replacement3, content)
        changes.append("Fixed function call site (removed flags argument)")

    # Fix 5: Also try a simpler pattern match
    pattern4 = r'ksu_umount_mnt\(&path, flags\)'
    replacement4 = 'ksu_umount_mnt(&path)'

    if pattern4 in content:
        content = content.replace(pattern4, replacement4)
        changes.append("Fixed function call site (simple replace)")

    # Check if any changes were made
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"SUCCESS: Fixed {filepath}")
        for change in changes:
            print(f"  - {change}")
        return True
    else:
        print(f"No changes needed for {filepath}")
        return False


def main():
    kernel_dir = os.environ.get('KERNEL_DIR', '')

    if len(sys.argv) > 1:
        kernel_dir = sys.argv[1]

    if not kernel_dir:
        print("Usage: KERNEL_DIR=/path/to/kernel python3 fix_kernelsu_49_v33.py [kernel_dir]")
        sys.exit(1)

    print(f"=== KernelSU-Next 4.9 Compatibility Fix v33 ===")
    print(f"Kernel directory: {kernel_dir}")

    # Find all possible locations of core_hook.c
    possible_paths = [
        os.path.join(kernel_dir, 'drivers/kernelsu/core_hook.c'),
        os.path.join(kernel_dir, 'KernelSU/kernel/core_hook.c'),
        os.path.join(kernel_dir, 'KernelSU-Next/kernel/core_hook.c'),
    ]

    fixed_any = False
    for path in possible_paths:
        real_path = os.path.realpath(path) if os.path.exists(path) else path
        if os.path.exists(real_path):
            print(f"\nProcessing: {real_path}")
            if fix_core_hook_file(real_path):
                fixed_any = True

    if fixed_any:
        print("\n=== Fix v33 applied successfully ===")
    else:
        print("\n=== No files needed fixing ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())
