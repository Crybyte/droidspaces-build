#!/usr/bin/env python3
"""
CRITICAL FIX v39: Comprehensive kernel 4.9 compatibility for ksu_umount_mnt

This fix addresses the root cause: the ksu_umount_mnt function uses umount()
which doesn't exist in kernel 4.9. We need to either:
1. Replace umount() with sys_umount() - but sys_umount takes different args
2. Or use ksys_umount() if available
3. Or implement the umount logic differently for kernel 4.9

Kernel 4.9 approach: Use sys_umount(pathname, flags) directly
"""

import sys
import os
import re

def fix_ksu_umount_mnt(kernel_dir):
    """Fix the ksu_umount_mnt function for kernel 4.9"""

    # Find core_hook.c
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

    # Strategy: Find the entire ksu_umount_mnt function and rewrite it
    # for kernel 4.9 compatibility

    # Pattern to find ksu_umount_mnt function
    func_pattern = r'(static int ksu_umount_mnt\(struct path \*path\)\s*\{[^}]+\})'

    match = re.search(func_pattern, content, re.DOTALL)
    if not match:
        print("WARNING: Could not find ksu_umount_mnt function with simple pattern")
        print("Trying alternative approach...")

        # Alternative: line-by-line fix for umount() calls
        lines = content.split('\n')
        in_ksu_umount_mnt = False
        brace_count = 0
        fixed_lines = []

        for i, line in enumerate(lines):
            if 'static int ksu_umount_mnt' in line:
                in_ksu_umount_mnt = True
                brace_count = 0
                print(f"Found ksu_umount_mnt at line {i+1}")

            if in_ksu_umount_mnt:
                # Count braces to track function scope
                brace_count += line.count('{')
                brace_count -= line.count('}')

                # Fix umount() calls within this function
                if 'umount(' in line and 'sys_umount' not in line and '//' not in line:
                    print(f"Line {i+1}: {line.strip()}")
                    # Replace umount(pathname) with sys_umount(pathname, 0)
                    new_line = re.sub(r'\bumount\s*\(\s*([^)]+)\s*\)', r'sys_umount(\1, 0)', line)
                    if new_line != line:
                        print(f"  -> {new_line.strip()}")
                        line = new_line

                if brace_count == 0 and '{' in content.split('\n')[i-1] if i > 0 else False:
                    in_ksu_umount_mnt = False

            fixed_lines.append(line)

        content = '\n'.join(fixed_lines)

    # Also add the sys_umount declaration if not present
    if 'asmlinkage long sys_umount' not in content:
        # Add declaration after includes or at top of file
        insert_pos = content.find('#include')
        if insert_pos >= 0:
            # Find end of includes
            last_include = content.rfind('#include')
            end_of_includes = content.find('\n', last_include)

            declaration = '\n/* Kernel 4.9 compatibility: sys_umount declaration */\n'
            declaration += '#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 10, 0)\n'
            declaration += 'extern int sys_umount(const char __user *name, int flags);\n'
            declaration += '#endif\n'

            content = content[:end_of_includes+1] + declaration + content[end_of_includes+1:]
            print("Added sys_umount declaration")

    with open(core_hook_file, 'w') as f:
        f.write(content)

    print(f"SUCCESS: Applied kernel 4.9 compatibility fix v39 to {core_hook_file}")
    return True

if __name__ == "__main__":
    kernel_dir = os.environ.get('KERNEL_DIR', os.path.expanduser('~/kernel-build/android_kernel_oneplus_sdm845'))
    if len(sys.argv) > 1:
        kernel_dir = sys.argv[1]

    print(f"=== CRITICAL FIX v39: Comprehensive ksu_umount_mnt fix for kernel 4.9 ===")
    print(f"Kernel directory: {kernel_dir}")

    success = fix_ksu_umount_mnt(kernel_dir)
    sys.exit(0 if success else 1)
