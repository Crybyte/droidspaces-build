#!/usr/bin/env python3
"""
KernelSU-Next 4.9 Compatibility Fix v36

This script fixes the 'undefined reference to umount' linker error.

In kernel 4.9, the umount() function is not exported. The ksu_umount_mnt function
calls umount(pathname) which fails to link. We need to replace this with a
kernel 4.9 compatible implementation.

Issue: aarch64-linux-gnu-ld: undefined reference to `umount'
       in function `ksu_umount_mnt' at core_hook.c:566

v36: More aggressive pattern matching and in-place function body replacement
"""

import os
import sys
import re
import glob

def find_core_hook(kernel_dir):
    """Find core_hook.c in various locations."""
    possible_paths = [
        os.path.join(kernel_dir, 'drivers', 'kernelsu', 'core_hook.c'),
        os.path.join(kernel_dir, 'KernelSU', 'kernel', 'core_hook.c'),
        os.path.join(kernel_dir, 'KernelSU-Next', 'kernel', 'core_hook.c'),
    ]

    # Follow symlinks
    for path in possible_paths:
        if os.path.islink(path):
            real_path = os.path.realpath(path)
            if os.path.exists(real_path):
                return real_path
        if os.path.exists(path):
            return path

    # Search recursively
    for root, dirs, files in os.walk(kernel_dir):
        if 'core_hook.c' in files:
            return os.path.join(root, 'core_hook.c')

    return None


def fix_umount_in_core_hook(kernel_dir):
    """
    Fix the umount() call in the ksu_umount_mnt function.
    """
    core_hook = find_core_hook(kernel_dir)

    if not core_hook:
        print(f"ERROR: Could not find core_hook.c in {kernel_dir}")
        return False

    print(f"Found core_hook.c at: {core_hook}")

    with open(core_hook, 'r') as f:
        lines = f.readlines()

    original_content = ''.join(lines)
    changes = []

    # First, let's see what's on the problematic lines around 566
    print("\n=== Line analysis around line 566 ===")
    for i in range(560, min(575, len(lines))):
        print(f"Line {i+1}: {lines[i].rstrip()}")

    # Process each line
    new_lines = []
    for i, line in enumerate(lines):
        original_line = line

        # Pattern 1: err = umount(pathname);
        if 'umount(' in line and 'sys_umount' not in line and 'ksu_umount' not in line:
            # Check for err = umount(...) pattern
            if re.search(r'err\s*=\s*umount\s*\(', line):
                line = re.sub(
                    r'err\s*=\s*umount\s*\(([^)]+)\)',
                    r'err = sys_umount(\1, 0)',
                    line
                )
                changes.append(f"Line {i+1}: err = umount(...) -> err = sys_umount(...)")

            # Pattern 2: return umount(...);
            elif re.search(r'return\s+umount\s*\(', line):
                line = re.sub(
                    r'return\s+umount\s*\(([^)]+)\)',
                    r'return sys_umount(\1, 0)',
                    line
                )
                changes.append(f"Line {i+1}: return umount(...) -> return sys_umount(...)")

            # Pattern 3: standalone umount(pathname) without assignment or return
            elif re.search(r'\bumount\s*\(', line):
                # Replace umount( with sys_umount( but preserve arguments
                line = re.sub(r'\bumount\s*\(', 'sys_umount(', line)
                # Add flags parameter if not present
                if '(' in line and 'sys_umount(' in line:
                    # Count commas in the function call to determine if flags is already there
                    match = re.search(r'sys_umount\(([^)]+)\)', line)
                    if match:
                        args = match.group(1)
                        if ',' not in args:
                            # Only one argument, add flags
                            line = line.replace(f'sys_umount({args})', f'sys_umount({args}, 0)')
                changes.append(f"Line {i+1}: umount(...) -> sys_umount(..., 0)")

        new_lines.append(line)

    content = ''.join(new_lines)

    # Add sys_umount declaration if sys_umount is used but not declared
    if 'sys_umount' in content and 'asmlinkage long sys_umount' not in content:
        # Find the last #include
        last_include_idx = -1
        lines_list = content.split('\n')
        for i, line in enumerate(lines_list):
            if line.strip().startswith('#include'):
                last_include_idx = i

        if last_include_idx >= 0:
            # Add syscalls.h include if not present
            has_syscalls = any('syscalls.h' in line for line in lines_list)
            if not has_syscalls:
                lines_list.insert(last_include_idx + 1, '#include <linux/syscalls.h>')
                changes.append("Added #include <linux/syscalls.h>")

            # Add sys_umount declaration
            declaration = 'asmlinkage long sys_umount(const char __user *name, int flags);'
            if declaration not in content:
                lines_list.insert(last_include_idx + 2, '/* Kernel 4.9 compatibility */')
                lines_list.insert(last_include_idx + 3, declaration)
                changes.append("Added sys_umount declaration")

            content = '\n'.join(lines_list)

    # Write back if changes were made
    if content != original_content:
        with open(core_hook, 'w') as f:
            f.write(content)
        print(f"\nSUCCESS: Fixed {core_hook}")
        for change in changes:
            print(f"  - {change}")

        # Verify by showing the fixed lines
        print("\n=== Fixed lines around 566 ===")
        with open(core_hook, 'r') as f:
            new_lines_check = f.readlines()
        for i in range(560, min(575, len(new_lines_check))):
            marker = " <--" if i >= 564 and i <= 568 else ""
            print(f"Line {i+1}: {new_lines_check[i].rstrip()}{marker}")

        return True
    else:
        print(f"\nNo changes made to {core_hook}")

        # Check if there are still umount calls that weren't fixed
        if 'umount(' in content and 'sys_umount' not in content:
            print("\nWARNING: Found umount() calls that weren't fixed!")
            for i, line in enumerate(content.split('\n'), 1):
                if 'umount(' in line and 'sys_umount' not in line and 'ksu_umount' not in line:
                    print(f"  Line {i}: {line.strip()}")
        elif 'sys_umount' in content:
            print("File already contains sys_umount - fix may already be applied")

        return False


def main():
    if len(sys.argv) < 2:
        kernel_dir = os.environ.get('KERNEL_DIR', '.')
    else:
        kernel_dir = sys.argv[1]

    print("=" * 60)
    print("KernelSU-Next 4.9 Compatibility Fix v36")
    print("Fixing undefined reference to umount()")
    print("=" * 60)
    print(f"Kernel directory: {kernel_dir}")
    print()

    fixed = fix_umount_in_core_hook(kernel_dir)

    print()
    print("=" * 60)
    if fixed:
        print("SUCCESS: Fixed umount references")
    else:
        print("WARNING: No fixes applied or already fixed")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
