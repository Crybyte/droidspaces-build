#!/usr/bin/env python3
"""
KernelSU-Next kernel 4.9 compatibility fix script v37
CRITICAL FIX: Remove -DKSU_UMOUNT from Makefile for kernel 4.9 compatibility

Issue: The KernelSU Makefile unconditionally adds -DKSU_UMOUNT to ccflags-y.
This causes the code to use path_umount() which doesn't exist in kernel 4.9.
When workflow patches replace path_umount with umount, it still fails because
umount also doesn't exist in kernel 4.9 (it's sys_umount).

Root Cause: The Makefile at KernelSU/kernel/Makefile adds:
    ccflags-y += -DKSU_UMOUNT

This forces the preprocessor to take this branch in core_hook.c:
    #if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 9, 0) || defined(KSU_UMOUNT)
        return path_umount(path, flags);  // Doesn't exist in 4.9!

Fix: Remove the -DKSU_UMOUNT flag from the Makefile so the code falls through
to the #else branch which returns -ENOSYS. This allows the kernel to compile
successfully. The umount functionality won't work, but KernelSU will still
function for root management.
"""

import sys
import os
import re

def fix_makefile(ksu_kernel_dir):
    """Remove -DKSU_UMOUNT from the KernelSU Makefile"""

    makefile_path = os.path.join(ksu_kernel_dir, 'Makefile')

    if not os.path.exists(makefile_path):
        print(f"ERROR: Makefile not found: {makefile_path}")
        return False

    with open(makefile_path, 'r') as f:
        content = f.read()

    original_content = content
    changes = []

    # Pattern 1: Remove -DKSU_UMOUNT from ccflags-y
    # Match lines like: ccflags-y += -DKSU_UMOUNT
    pattern1 = r'^(ccflags-y\s*\+?=\s*-DKSU_UMOUNT)\s*$'
    replacement1 = r'# \1  # REMOVED for kernel 4.9 compatibility - falls back to -ENOSYS'

    if re.search(pattern1, content, re.MULTILINE):
        content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)
        changes.append("Commented out -DKSU_UMOUNT from ccflags-y")

    # Pattern 2: Handle multiple flags on same line
    # ccflags-y += -DKSU_UMOUNT -Wsomething
    pattern2 = r'^(ccflags-y\s*\+?=\s.*)(-DKSU_UMOUNT)(.*)$'
    def replace_flag(match):
        return f'{match.group(1)}# {match.group(2)} removed for kernel 4.9{match.group(3)}'

    if re.search(pattern2, content, re.MULTILINE):
        content = re.sub(pattern2, replace_flag, content, flags=re.MULTILINE)
        changes.append("Removed -DKSU_UMOUNT from multi-flag ccflags-y line")

    # Pattern 3: Check for any remaining -DKSU_UMOUNT definitions
    remaining = re.findall(r'-DKSU_UMOUNT', content)
    if remaining and content == original_content:
        print(f"WARNING: Found {len(remaining)} -DKSU_UMOUNT occurrences but couldn't patch them")
        # Show the lines for debugging
        for i, line in enumerate(content.split('\n'), 1):
            if '-DKSU_UMOUNT' in line:
                print(f"  Line {i}: {line.strip()}")

    # Check if any changes were made
    if content != original_content:
        with open(makefile_path, 'w') as f:
            f.write(content)
        print(f"SUCCESS: Fixed {makefile_path}")
        for change in changes:
            print(f"  - {change}")
        return True
    else:
        print(f"No changes needed for {makefile_path}")
        return False


def verify_core_hook_no_ksu_umount(ksu_kernel_dir):
    """Verify that core_hook.c won't try to use path_umount with KSU_UMOUNT disabled"""

    core_hook_path = os.path.join(ksu_kernel_dir, 'core_hook.c')

    if not os.path.exists(core_hook_path):
        print(f"INFO: core_hook.c not found at {core_hook_path}")
        return True

    with open(core_hook_path, 'r') as f:
        content = f.read()

    # Check if there's a fallback implementation for non-KSU_UMOUNT case
    if '#else' in content and 'path_umount' in content:
        print("INFO: core_hook.c has both KSU_UMOUNT and fallback paths - good")
        return True

    # Check for the TODO comment which indicates the fallback
    if 'TODO: umount for non GKI kernel' in content:
        print("INFO: core_hook.c has the TODO fallback comment - will use -ENOSYS")
        return True

    print("WARNING: core_hook.c structure unknown - may still fail")
    return False


def main():
    kernel_dir = os.environ.get('KERNEL_DIR', '')

    if len(sys.argv) > 1:
        kernel_dir = sys.argv[1]

    if not kernel_dir:
        print("Usage: KERNEL_DIR=/path/to/kernel python3 fix_kernelsu_49_v37.py [kernel_dir]")
        sys.exit(1)

    print(f"=== KernelSU-Next 4.9 Compatibility Fix v37 ===")
    print(f"Kernel directory: {kernel_dir}")
    print("")
    print("This fix removes -DKSU_UMOUNT from the KernelSU Makefile.")
    print("This prevents the code from calling path_umount() which doesn't exist in kernel 4.9.")
    print("")

    # Find all possible locations of KernelSU Makefile
    possible_paths = [
        os.path.join(kernel_dir, 'drivers/kernelsu'),  # Symlink target
        os.path.join(kernel_dir, 'KernelSU/kernel'),
        os.path.join(kernel_dir, 'KernelSU-Next/kernel'),
    ]

    fixed_any = False
    for path in possible_paths:
        real_path = os.path.realpath(path) if os.path.exists(path) else path
        if os.path.exists(real_path):
            print(f"\nProcessing: {real_path}")
            if fix_makefile(real_path):
                fixed_any = True
            verify_core_hook_no_ksu_umount(real_path)

    if fixed_any:
        print("\n=== Fix v37 applied successfully ===")
        print("The kernel should now compile without undefined reference to umount/path_umount")
    else:
        print("\n=== No files needed fixing ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())
