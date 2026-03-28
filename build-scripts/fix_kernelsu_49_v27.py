#!/usr/bin/env python3
"""
KernelSU-Next v1.0.7 kernel 4.9 compatibility fixer v27
CRITICAL FIX: Patches BOTH the symlink target AND the symlink itself

Key insight: The compiler uses drivers/kernelsu (symlink) but our patches
might be applied to the wrong physical location. This fix ensures we patch
the exact file the compiler reads.
"""

import sys
import re
import os
import subprocess

def get_real_file_path(path):
    """Get the canonical path that the compiler will actually read"""
    try:
        # Use readlink -f to get the ultimate target
        result = subprocess.run(['readlink', '-f', path], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return os.path.realpath(path)

def fix_core_hook(filepath):
    """Fix core_hook.c for kernel 4.9 compatibility - v27 critical fix"""

    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return False

    # Get the canonical path
    canonical_path = get_real_file_path(filepath)
    print(f"Canonical path: {canonical_path}")

    # Read the file
    with open(canonical_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')

    fixes_applied = []
    modified = False

    # Show line 591 specifically (0-indexed = 590)
    if len(lines) > 590:
        print(f"\nLine 591 (before fix): {lines[590]}")

    # Fix 1: Direct string replacement for ksu_umount_mnt(&path, flags)
    if 'ksu_umount_mnt(&path, flags)' in content:
        content = content.replace('ksu_umount_mnt(&path, flags)', 'ksu_umount_mnt(&path)')
        fixes_applied.append("Fixed ksu_umount_mnt(&path, flags)")
        modified = True

    # Fix 2: Pattern match ksu_umount_mnt with any first arg and flags as second
    new_content, count = re.subn(
        r'ksu_umount_mnt\s*\(\s*([^,)]+)\s*,\s*flags\s*\)',
        r'ksu_umount_mnt(\1)',
        content
    )
    if count > 0:
        fixes_applied.append(f"Fixed {count} ksu_umount_mnt(..., flags) calls")
        content = new_content
        modified = True

    # Fix 3: Fix 3-argument try_umount calls
    new_content, count = re.subn(
        r'try_umount\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*[^)]+\s*\)',
        r'try_umount(\1, \2)',
        content
    )
    if count > 0:
        fixes_applied.append(f"Fixed {count} 3-arg try_umount calls")
        content = new_content
        modified = True

    # Fix 4: Function signature - ksu_umount_mnt(struct path *path, int flags)
    new_content, count = re.subn(
        r'static\s+int\s+ksu_umount_mnt\s*\(\s*struct\s+path\s*\*\s*\w+\s*,\s*int\s+\w+\s*\)',
        'static int ksu_umount_mnt(struct path *path)',
        content
    )
    if count > 0:
        fixes_applied.append(f"Fixed ksu_umount_mnt signature ({count})")
        content = new_content
        modified = True

    # Fix 5: try_umount signature with flags
    new_content, count = re.subn(
        r'static\s+void\s+try_umount\s*\(\s*const\s+char\s*\*\s*\w+\s*,\s*bool\s+\w+\s*,\s*int\s+\w+\s*\)',
        'static void try_umount(const char *mnt, bool check_mnt)',
        content
    )
    if count > 0:
        fixes_applied.append(f"Fixed try_umount signature ({count})")
        content = new_content
        modified = True

    # Fix 6: Remove 'int flags' variable declarations that are no longer needed
    new_content, count = re.subn(
        r'int\s+flags\s*=\s*[^;]+;',
        '',
        content
    )
    if count > 0:
        fixes_applied.append(f"Removed {count} flags variable declarations")
        content = new_content
        modified = True

    # Fix 7: Remove unused 'flags' parameters in function bodies
    new_content, count = re.subn(
        r',\s*\n\s*int\s+flags\s*\)',
        ')',
        content
    )
    if count > 0:
        fixes_applied.append(f"Fixed {count} multi-line flags params")
        content = new_content
        modified = True

    # Fix 8: path_umount calls
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
        # Write back to the canonical path
        with open(canonical_path, 'w') as f:
            f.write(content)

        # Also write to the symlink path if different
        if canonical_path != filepath and os.path.exists(filepath):
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"✓ Fixed {filepath} -> {canonical_path}")
        else:
            print(f"✓ Fixed {canonical_path}")

        for fix in fixes_applied:
            print(f"  - {fix}")

        # Show line 591 after fix
        lines_after = content.split('\n')
        if len(lines_after) > 590:
            print(f"\nLine 591 (after fix): {lines_after[590]}")

        return True
    else:
        print(f"No changes needed for {filepath}")
        return False


def main():
    if len(sys.argv) > 1:
        ksu_dir = sys.argv[1]
    else:
        ksu_dir = os.environ.get('KSU_DIR', 'KernelSU/kernel')

    print(f"=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fixer v27 ===")
    print(f"Input KSU_DIR: {ksu_dir}")

    # Try multiple possible locations
    locations = [
        os.path.join(ksu_dir, 'core_hook.c'),
        'drivers/kernelsu/core_hook.c',
        '../drivers/kernelsu/core_hook.c',
        'KernelSU/kernel/core_hook.c',
        '../KernelSU/kernel/core_hook.c',
    ]

    fixed_any = False
    for loc in locations:
        if os.path.exists(loc):
            print(f"\nFound: {loc}")
            success = fix_core_hook(loc)
            if success:
                fixed_any = True

    if fixed_any:
        print("\n✓ Fixes applied successfully")
        sys.exit(0)
    else:
        print("\n✗ No files found to fix")
        sys.exit(1)


if __name__ == '__main__':
    main()
