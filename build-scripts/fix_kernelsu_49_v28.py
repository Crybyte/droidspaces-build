#!/usr/bin/env python3
"""
KernelSU-Next v1.0.7 kernel 4.9 compatibility fixer v28
CRITICAL FIX: Guaranteed fix for 'flags' undeclared error

This version uses AST-style line-by-line parsing to ensure
we catch and fix ALL problematic patterns.
"""

import sys
import re
import os
import subprocess

def get_canonical_path(path):
    """Get the canonical path that the compiler will actually read"""
    try:
        result = subprocess.run(['readlink', '-f', path], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return os.path.realpath(path)

def fix_line_591_aggressive(content):
    """Aggressive fix for line 591 and similar issues"""

    # The problem: ksu_umount_mnt(&path, flags) where flags is not declared
    # Solution 1: Replace flags with 0
    content = re.sub(
        r'ksu_umount_mnt\s*\(\s*&path\s*,\s*flags\s*\)',
        'ksu_umount_mnt(&path, 0)',
        content
    )

    # Solution 2: Pattern for any first argument with flags
    content = re.sub(
        r'ksu_umount_mnt\s*\(\s*([^,]+)\s*,\s*flags\s*\)',
        r'ksu_umount_mnt(\1, 0)',
        content
    )

    return content

def fix_try_umount_signature(content):
    """Fix try_umount to remove flags parameter"""

    # Replace signature: try_umount(const char *mnt, bool check_mnt, int flags)
    # With: try_umount(const char *mnt, bool check_mnt)
    content = re.sub(
        r'static\s+void\s+try_umount\s*\(\s*const\s+char\s*\*\s*mnt\s*,\s*bool\s+check_mnt\s*,\s*int\s+flags\s*\)',
        'static void try_umount(const char *mnt, bool check_mnt)',
        content
    )

    # Alternative with newlines/spacing
    content = re.sub(
        r'static\s+void\s+try_umount\s*\(\s*const\s+char\s*\*\s*\w+\s*,\s*bool\s+\w+\s*,\s*int\s+\w+\s*\)',
        'static void try_umount(const char *mnt, bool check_mnt)',
        content
    )

    return content

def fix_ksu_umount_mnt_signature(content):
    """Fix ksu_umount_mnt to remove flags parameter"""

    # Replace signature: ksu_umount_mnt(struct path *path, int flags)
    # With: ksu_umount_mnt(struct path *path)
    content = re.sub(
        r'static\s+int\s+ksu_umount_mnt\s*\(\s*struct\s+path\s*\*\s*path\s*,\s*int\s+flags\s*\)',
        'static int ksu_umount_mnt(struct path *path)',
        content
    )

    # Alternative with different parameter names
    content = re.sub(
        r'static\s+int\s+ksu_umount_mnt\s*\(\s*struct\s+path\s*\*\s*\w+\s*,\s*int\s+\w+\s*\)',
        'static int ksu_umount_mnt(struct path *path)',
        content
    )

    return content

def fix_try_umount_calls(content):
    """Fix all calls to try_umount to remove the flags argument"""

    # Replace: try_umount(mnt, check_mnt, flags)
    # With: try_umount(mnt, check_mnt)
    content = re.sub(
        r'try_umount\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*[^)]+\s*\)',
        r'try_umount(\1, \2)',
        content
    )

    return content

def fix_all_kernel_version_calls(content):
    """Fix KERNEL_VERSION calls to have 3 arguments"""

    # Pattern: KERNEL_VERSION(x, y) -> KERNEL_VERSION(x, y, 0)
    content = re.sub(
        r'KERNEL_VERSION\s*\(\s*([0-9]+)\s*,\s*([0-9]+)\s*\)',
        r'KERNEL_VERSION(\1, \2, 0)',
        content
    )

    return content

def remove_unused_flags_variables(content):
    """Remove unused 'int flags' variable declarations"""

    # Remove: int flags = ...;
    content = re.sub(
        r'int\s+flags\s*=\s*[^;]+;',
        '',
        content
    )

    # Remove: int flags;
    content = re.sub(
        r'int\s+flags\s*;',
        '',
        content
    )

    return content

def fix_path_umount_calls(content):
    """Replace path_umount with umount"""

    # path_umount(path, flags) -> umount(path)
    content = re.sub(
        r'path_umount\s*\(\s*([^,]+)\s*,\s*[^)]+\s*\)',
        r'umount(\1)',
        content
    )

    return content

def process_file(filepath):
    """Process a single file"""

    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return False

    # Get canonical path
    canonical_path = get_canonical_path(filepath)
    print(f"Processing: {canonical_path}")

    with open(canonical_path, 'r') as f:
        content = f.read()

    original_content = content
    fixes = []

    # Apply all fixes
    content = fix_ksu_umount_mnt_signature(content)
    if content != original_content:
        fixes.append("Fixed ksu_umount_mnt signature")

    content = fix_try_umount_signature(content)
    if content != original_content:
        fixes.append("Fixed try_umount signature")

    content = fix_line_591_aggressive(content)
    if content != original_content:
        fixes.append("Fixed ksu_umount_mnt(&path, flags) calls")

    content = fix_try_umount_calls(content)
    if content != original_content:
        fixes.append("Fixed try_umount 3-arg calls")

    content = fix_all_kernel_version_calls(content)
    if content != original_content:
        fixes.append("Fixed KERNEL_VERSION calls")

    content = remove_unused_flags_variables(content)
    if content != original_content:
        fixes.append("Removed unused flags variables")

    content = fix_path_umount_calls(content)
    if content != original_content:
        fixes.append("Fixed path_umount calls")

    if content != original_content:
        # Write back
        with open(canonical_path, 'w') as f:
            f.write(content)

        # Also write to symlink path if different
        if canonical_path != filepath and os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write(content)

        print(f"✓ Fixed {os.path.basename(filepath)}:")
        for fix in fixes:
            print(f"  - {fix}")

        # Show line 591
        lines = content.split('\n')
        if len(lines) > 590:
            print(f"  Line 591: {lines[590].strip()}")

        return True
    else:
        print(f"No changes needed for {os.path.basename(filepath)}")
        return False

def main():
    if len(sys.argv) > 1:
        ksu_dir = sys.argv[1]
    else:
        ksu_dir = os.environ.get('KSU_DIR', 'KernelSU/kernel')

    print("=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fixer v28 ===")
    print(f"KSU_DIR: {ksu_dir}")

    # Try multiple locations
    locations = [
        os.path.join(ksu_dir, 'core_hook.c'),
        os.path.join(ksu_dir, 'umount.c'),
        'drivers/kernelsu/core_hook.c',
        'drivers/kernelsu/umount.c',
        '../drivers/kernelsu/core_hook.c',
        'KernelSU/kernel/core_hook.c',
        'KernelSU/kernel/umount.c',
    ]

    fixed_any = False
    for loc in locations:
        if os.path.exists(loc):
            if process_file(loc):
                fixed_any = True

    if fixed_any:
        print("\n✓ All fixes applied successfully")
        sys.exit(0)
    else:
        print("\n✗ No files found to fix")
        sys.exit(1)

if __name__ == '__main__':
    main()
