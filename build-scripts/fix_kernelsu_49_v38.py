#!/usr/bin/env python3
"""
KernelSU-Next kernel 4.9 compatibility fix script v38
CRITICAL FIX: Replace umount() with sys_umount() for kernel 4.9 compatibility

Issue: The pre-patched core_hook.c.patched file at line 583 calls umount(pathname)
which doesn't exist in kernel 4.9. Kernel 4.9 uses sys_umount() for the umount syscall.

Root Cause: 
- Line 583: err = umount(pathname);
- This should be: err = sys_umount(pathname, 0);

Fix: Replace all umount() calls with sys_umount() calls in core_hook.c
Also add the proper include for syscalls if needed.

Additional: Add declaration for sys_umount if not present in headers.
"""

import sys
import os
import re

def fix_umount_calls(core_hook_path):
    """Replace umount() with sys_umount() in core_hook.c"""

    if not os.path.exists(core_hook_path):
        print(f"ERROR: core_hook.c not found: {core_hook_path}")
        return False

    with open(core_hook_path, 'r') as f:
        content = f.read()

    original_content = content
    changes = []

    # Pattern 1: Replace umount(pathname) with sys_umount(pathname, 0)
    # This handles the common pattern: err = umount(pathname);
    pattern1 = r'(?<!sys_)(\b)umount\s*\(\s*(\w+)\s*\)'
    replacement1 = r'sys_umount(\2, 0)'

    matches = re.findall(pattern1, content)
    if matches:
        content = re.sub(pattern1, replacement1, content)
        changes.append(f"Replaced umount() with sys_umount() in {len(matches)} location(s)")
        for match in matches:
            print(f"  Found: umount({match[1]})")

    # Pattern 2: Check for any remaining umount calls that weren't caught
    remaining = re.findall(r'(?<!sys_)(?<!)try_)\bumount\s*\(', content)
    if remaining:
        print(f"WARNING: Found {len(remaining)} remaining umount() calls:")
        for i, line in enumerate(content.split('\n'), 1):
            if re.search(r'(?<!sys_)(?<!)try_)\bumount\s*\(', line):
                print(f"  Line {i}: {line.strip()}")

    # Pattern 3: Fix the ksu_umount_mnt function to use sys_umount properly
    # The function currently calls umount(pathname) but should call sys_umount
    if 'sys_umount' not in content:
        print("WARNING: No sys_umount calls found after patching!")

    # Check if any changes were made
    if content != original_content:
        with open(core_hook_path, 'w') as f:
            f.write(content)
        print(f"SUCCESS: Fixed {core_hook_path}")
        for change in changes:
            print(f"  - {change}")
        return True
    else:
        print(f"No umount() changes needed for {core_hook_path}")
        return False


def add_sys_umount_declaration(core_hook_path):
    """Add extern declaration for sys_umount if not present"""

    with open(core_hook_path, 'r') as f:
        content = f.read()

    # Check if sys_umount is already declared
    if 'asmlinkage long sys_umount' in content or 'extern long sys_umount' in content:
        print("INFO: sys_umount declaration already present")
        return False

    # Add declaration after the includes
    declaration = '''
/* Kernel 4.9 compatibility: Declare sys_umount */
asmlinkage long sys_umount(const char __user *name, int flags);
'''

    # Find a good place to insert (after includes, before first function)
    lines = content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('#include'):
            insert_idx = i + 1

    lines.insert(insert_idx, declaration)
    content = '\n'.join(lines)

    with open(core_hook_path, 'w') as f:
        f.write(content)

    print("SUCCESS: Added sys_umount declaration")
    return True


def fix_pre_patched_file(build_scripts_dir):
    """Also fix the core_hook.c.patched file for future builds"""

    patched_file = os.path.join(build_scripts_dir, 'core_hook.c.patched')
    if not os.path.exists(patched_file):
        print(f"INFO: Pre-patched file not found: {patched_file}")
        return False

    print(f"\n=== Also fixing pre-patched file: {patched_file} ===")

    with open(patched_file, 'r') as f:
        content = f.read()

    original_content = content

    # Replace umount(pathname) with sys_umount(pathname, 0)
    pattern = r'(?<!sys_)(\b)umount\s*\(\s*(\w+)\s*\)'
    replacement = r'sys_umount(\2, 0)'

    content = re.sub(pattern, replacement, content)

    if content != original_content:
        with open(patched_file, 'w') as f:
            f.write(content)
        print("SUCCESS: Fixed pre-patched core_hook.c.patched file")
        return True
    else:
        print("No changes needed for pre-patched file")
        return False


def main():
    kernel_dir = os.environ.get('KERNEL_DIR', '')

    if len(sys.argv) > 1:
        kernel_dir = sys.argv[1]

    if not kernel_dir:
        print("Usage: KERNEL_DIR=/path/to/kernel python3 fix_kernelsu_49_v38.py [kernel_dir]")
        sys.exit(1)

    print(f"=== KernelSU-Next 4.9 Compatibility Fix v38 ===")
    print(f"Kernel directory: {kernel_dir}")
    print("")
    print("This fix replaces umount() with sys_umount() for kernel 4.9 compatibility.")
    print("")

    # Find core_hook.c in all possible locations
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
            if fix_umount_calls(real_path):
                fixed_any = True
            if add_sys_umount_declaration(real_path):
                fixed_any = True

    # Also fix the pre-patched file in build-scripts
    build_scripts_dir = os.path.join(os.path.dirname(__file__), 'build-scripts')
    if not os.path.exists(build_scripts_dir):
        # Try repo root
        build_scripts_dir = os.path.dirname(__file__)

    if fix_pre_patched_file(build_scripts_dir):
        fixed_any = True

    if fixed_any:
        print("\n=== Fix v38 applied successfully ===")
        print("The kernel should now compile without undefined reference to umount")
    else:
        print("\n=== No files needed fixing ===")

    return 0


if __name__ == "__main__":
    sys.exit(main())
