#!/usr/bin/env python3
"""
KernelSU-Next kernel 4.9 compatibility fix script v39
FINAL FIX: Aggressive umount() -> sys_umount() replacement for kernel 4.9

Issue: The pre-patched core_hook.c.patched file contains umount() calls
which don't exist in kernel 4.9. This fix runs AFTER the pre-patched file
is applied to ensure all umount calls are replaced.

This fix is designed to be the FINAL and MOST AGGRESSIVE fix.
"""

import sys
import os
import re

def aggressive_umount_fix(file_path):
    """Aggressively replace all umount() calls with sys_umount()"""

    if not os.path.exists(file_path):
        return False, "File not found"

    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content
    changes = []

    # Pattern 1: Direct umount(something) -> sys_umount(something, 0)
    # This is the most common pattern causing the undefined reference
    pattern1 = r'(?<!sys_)(?<!try_)\bumount\s*\(\s*([^,)]+)\s*\)'
    matches1 = list(re.finditer(pattern1, content))
    if matches1:
        content = re.sub(pattern1, r'sys_umount(\1, 0)', content)
        changes.append(f"Replaced {len(matches1)} umount(X) calls with sys_umount(X, 0)")

    # Pattern 2: Handle any remaining umount with two args (shouldn't exist but be safe)
    pattern2 = r'(?<!sys_)(?<!try_)\bumount\s*\('
    matches2 = list(re.finditer(pattern2, content))
    if matches2:
        changes.append(f"WARNING: Found {len(matches2)} remaining umount calls that need manual fix")
        for i, match in enumerate(matches2):
            # Get surrounding context
            start = max(0, match.start() - 20)
            end = min(len(content), match.end() + 40)
            context = content[start:end]
            changes.append(f"  Match {i+1}: ...{context}...")

    # Check if any changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True, changes
    else:
        return False, "No umount() calls found to fix"


def ensure_sys_umount_declaration(file_path):
    """Ensure sys_umount is declared for kernel 4.9"""

    with open(file_path, 'r') as f:
        content = f.read()

    # Check if already declared
    if 'asmlinkage long sys_umount' in content or 'extern long sys_umount' in content:
        return False, "sys_umount already declared"

    # Add declaration after includes
    declaration = '''/* Kernel 4.9 compatibility */
asmlinkage long sys_umount(const char __user *name, int flags);
'''

    # Find last #include line
    lines = content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('#include'):
            insert_idx = i + 1

    lines.insert(insert_idx, declaration)
    content = '\n'.join(lines)

    with open(file_path, 'w') as f:
        f.write(content)

    return True, "Added sys_umount declaration"


def process_core_hook_files(kernel_dir):
    """Process all possible core_hook.c locations"""

    possible_paths = [
        os.path.join(kernel_dir, 'drivers/kernelsu/core_hook.c'),
        os.path.join(kernel_dir, 'drivers/kernelsu/KernelSU/kernel/core_hook.c'),
        os.path.join(kernel_dir, 'KernelSU/kernel/core_hook.c'),
        os.path.join(kernel_dir, 'KernelSU-Next/kernel/core_hook.c'),
    ]

    results = []
    for path in possible_paths:
        real_path = os.path.realpath(path) if os.path.exists(path) else path
        if os.path.exists(real_path):
            print(f"\nProcessing: {real_path}")

            # Apply aggressive umount fix
            fixed, msg = aggressive_umount_fix(real_path)
            if fixed:
                print(f"  [FIXED] {msg}")
            else:
                print(f"  [INFO] {msg}")

            # Ensure declaration exists
            declared, msg = ensure_sys_umount_declaration(real_path)
            if declared:
                print(f"  [DECLARED] {msg}")

            results.append((real_path, fixed, declared))

    return results


def main():
    kernel_dir = os.environ.get('KERNEL_DIR', '')

    if len(sys.argv) > 1:
        kernel_dir = sys.argv[1]

    if not kernel_dir:
        print("Usage: KERNEL_DIR=/path/to/kernel python3 fix_kernelsu_49_v39.py [kernel_dir]")
        sys.exit(1)

    print("=" * 60)
    print("KernelSU-Next 4.9 Compatibility Fix v39 (FINAL)")
    print("=" * 60)
    print(f"Kernel directory: {kernel_dir}")
    print("")
    print("This fix aggressively replaces ALL umount() calls with sys_umount()")
    print("It runs AFTER the pre-patched file is applied.")
    print("")

    results = process_core_hook_files(kernel_dir)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if results:
        for path, fixed, declared in results:
            status = "FIXED" if fixed else "OK"
            print(f"  [{status}] {path}")
        print("\nv39 fix applied. Build should now succeed.")
        return 0
    else:
        print("  WARNING: No core_hook.c files found!")
        print(f"  Searched in: {kernel_dir}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
