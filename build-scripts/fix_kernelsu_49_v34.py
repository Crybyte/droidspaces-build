#!/usr/bin/env python3
"""
KernelSU-Next 4.9 Compatibility Fix v34

This script fixes the 'undefined reference to umount' linker error.

In kernel 4.9, the umount() function is not exported. The ksu_umount_mnt function
calls umount(path->mnt) which fails to link. We need to replace this with a
kernel 4.9 compatible implementation using ksys_umount or the sys_umount syscall.

Issue: aarch64-linux-gnu-ld: undefined reference to `umount'
       in function `ksu_umount_mnt' at core_hook.c:566
"""

import os
import sys
import re
import glob

def fix_umount_call(filepath):
    """
    Fix the umount() call in ksu_umount_mnt function.
    
    The function calls umount(path->mnt) which doesn't exist in kernel 4.9.
    We replace it with a compatible implementation using ksys_umount.
    """
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Pattern 1: umount(path->mnt) - the most common pattern
    # Replace with ksys_umount(path->mnt->mnt_root, MNT_DETACH)
    pattern1 = r'return\s+umount\s*\(\s*path->mnt\s*\)'
    if re.search(pattern1, content):
        content = re.sub(
            pattern1,
            'return ksys_umount(path->mnt->mnt_devname, MNT_DETACH)',
            content
        )
        changes.append("Fixed umount(path->mnt) -> ksys_umount")
    
    # Pattern 2: umount(mnt) - generic pattern
    pattern2 = r'return\s+umount\s*\(\s*mnt\s*\)'
    if re.search(pattern2, content):
        content = re.sub(
            pattern2,
            'return ksys_umount(mnt->mnt_devname, MNT_DETACH)',
            content
        )
        changes.append("Fixed umount(mnt) -> ksys_umount")
    
    # Pattern 3: umount with any argument
    pattern3 = r'\bumount\s*\('
    if re.search(pattern3, content) and not 'ksys_umount' in content:
        # Replace any remaining umount calls
        content = re.sub(r'\bumount\s*\(', 'ksys_umount(', content)
        changes.append("Fixed generic umount() calls -> ksys_umount()")
    
    # Write back if changes were made
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True, changes
    
    return False, []


def add_umount_header_include(filepath):
    """
    Ensure the proper headers are included for ksys_umount.
    We need linux/syscalls.h or linux/mount.h
    """
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Check if we already have syscalls.h include
    if 'syscalls.h' not in content:
        # Add #include <linux/syscalls.h> after the last #include
        # Find the last #include line
        lines = content.split('\n')
        last_include_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('#include'):
                last_include_idx = i
        
        if last_include_idx >= 0:
            # Insert after the last include
            lines.insert(last_include_idx + 1, '#include <linux/syscalls.h>')
            content = '\n'.join(lines)
            changes.append("Added #include <linux/syscalls.h>")
    
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        return True, changes
    
    return False, []


def fix_core_hook_file(kernel_dir):
    """Fix the core_hook.c file that contains the umount call."""
    
    # Find all possible locations of core_hook.c
    possible_paths = [
        os.path.join(kernel_dir, 'drivers/kernelsu/core_hook.c'),
        os.path.join(kernel_dir, 'KernelSU/kernel/core_hook.c'),
        os.path.join(kernel_dir, 'KernelSU-Next/kernel/core_hook.c'),
    ]
    
    # Also check if drivers/kernelsu is a symlink and follow it
    drivers_kernelsu = os.path.join(kernel_dir, 'drivers/kernelsu')
    if os.path.islink(drivers_kernelsu):
        real_path = os.path.realpath(drivers_kernelsu)
        if os.path.isdir(real_path):
            possible_paths.append(os.path.join(real_path, 'core_hook.c'))
    
    fixed_files = []
    
    for filepath in possible_paths:
        if os.path.exists(filepath):
            print(f"Processing: {filepath}")
            
            # First, add the necessary header
            header_fixed, header_changes = add_umount_header_include(filepath)
            
            # Then fix the umount calls
            umount_fixed, umount_changes = fix_umount_call(filepath)
            
            if header_fixed or umount_fixed:
                fixed_files.append({
                    'path': filepath,
                    'changes': header_changes + umount_changes
                })
                print(f"  SUCCESS: Fixed {filepath}")
                for change in header_changes + umount_changes:
                    print(f"    - {change}")
            else:
                print(f"  No changes needed for {filepath}")
    
    return fixed_files


def main():
    if len(sys.argv) < 2:
        kernel_dir = os.environ.get('KERNEL_DIR', '.')
    else:
        kernel_dir = sys.argv[1]
    
    print("=" * 60)
    print("KernelSU-Next 4.9 Compatibility Fix v34")
    print("Fixing undefined reference to umount()")
    print("=" * 60)
    print(f"Kernel directory: {kernel_dir}")
    print()
    
    fixed_files = fix_core_hook_file(kernel_dir)
    
    print()
    print("=" * 60)
    if fixed_files:
        print(f"SUCCESS: Fixed {len(fixed_files)} file(s)")
        for f in fixed_files:
            print(f"  - {f['path']}")
    else:
        print("No files were modified")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
