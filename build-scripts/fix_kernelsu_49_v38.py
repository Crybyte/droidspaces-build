#!/usr/bin/env python3
"""
CRITICAL FIX v38: Replace umount() with sys_umount() for kernel 4.9 compatibility

Kernel 4.9 does not have umount() syscall wrapper - it uses sys_umount(path, flags)
This script replaces all umount() calls with sys_umount() calls.
"""

import sys
import os
import re

def fix_umount_calls(kernel_dir):
    """Replace umount() with sys_umount() in core_hook.c"""

    # Find core_hook.c in various locations
    possible_paths = [
        os.path.join(kernel_dir, "drivers", "kernelsu", "core_hook.c"),
        os.path.join(kernel_dir, "KernelSU", "kernel", "core_hook.c"),
        os.path.join(kernel_dir, "KernelSU-Next", "kernel", "core_hook.c"),
    ]

    core_hook_file = None
    for path in possible_paths:
        if os.path.exists(path):
            core_hook_file = path
            break

    if not core_hook_file:
        print("ERROR: Could not find core_hook.c")
        return False

    print(f"Found core_hook.c at: {core_hook_file}")

    with open(core_hook_file, 'r') as f:
        content = f.read()
        lines = content.split('\n')

    print(f"File has {len(lines)} lines")

    # Find the ksu_umount_mnt function and replace umount() with sys_umount()
    fixed_count = 0
    for i, line in enumerate(lines):
        # Match umount(pathname) or umount(mnt) or umount(any_variable)
        # but NOT comments or string literals
        if re.search(r'\bumount\s*\([^)]+\)', line) and not line.strip().startswith('//'):
            # Check if it's already sys_umount
            if 'sys_umount' not in line:
                print(f"Line {i+1} BEFORE: {line.strip()}")
                # Replace umount(arg) with sys_umount(arg, 0)
                new_line = re.sub(r'\bumount\s*\(\s*([^)]+)\s*\)', r'sys_umount(\1, 0)', line)
                lines[i] = new_line
                fixed_count += 1
                print(f"Line {i+1} AFTER: {new_line.strip()}")

    if fixed_count > 0:
        print(f"\nFixed {fixed_count} umount() calls")

        # Write the fixed content back
        with open(core_hook_file, 'w') as f:
            f.write('\n'.join(lines))

        print(f"SUCCESS: Fixed {fixed_count} umount() calls in {core_hook_file}")
        return True
    else:
        print("No umount() calls found to fix")
        return True

if __name__ == "__main__":
    kernel_dir = os.environ.get('KERNEL_DIR', os.path.expanduser('~/kernel-build/android_kernel_oneplus_sdm845'))
    if len(sys.argv) > 1:
        kernel_dir = sys.argv[1]

    print(f"=== CRITICAL FIX v38: Replacing umount() with sys_umount() ===")
    print(f"Kernel directory: {kernel_dir}")

    success = fix_umount_calls(kernel_dir)
    sys.exit(0 if success else 1)
