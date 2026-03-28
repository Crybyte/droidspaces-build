#!/usr/bin/env python3
"""
KernelSU-Next 4.9 Compatibility Fix v35

This script fixes the 'undefined reference to umount' linker error.

In kernel 4.9, the umount() function is not exported. The ksu_umount_mnt function
calls umount(pathname) which fails to link. We need to replace this with a
kernel 4.9 compatible implementation using sys_umount syscall.

Issue: aarch64-linux-gnu-ld: undefined reference to `umount'
       in function `ksu_umount_mnt' at core_hook.c:566
"""

import os
import sys
import re
import glob

def fix_umount_in_core_hook(kernel_dir):
    """
    Fix the umount() call in the ksu_umount_mnt function.
    
    The function calls umount(pathname) which doesn't exist in kernel 4.9.
    We replace it with sys_umount syscall for kernel 4.9 compatibility.
    """
    # Find core_hook.c in various locations
    possible_paths = [
        os.path.join(kernel_dir, 'drivers', 'kernelsu', 'core_hook.c'),
        os.path.join(kernel_dir, 'KernelSU', 'kernel', 'core_hook.c'),
    ]
    
    core_hook = None
    for path in possible_paths:
        if os.path.exists(path):
            core_hook = path
            break
    
    if not core_hook:
        # Search recursively
        for root, dirs, files in os.walk(kernel_dir):
            if 'core_hook.c' in files:
                core_hook = os.path.join(root, 'core_hook.c')
                break
    
    if not core_hook:
        print(f"ERROR: Could not find core_hook.c in {kernel_dir}")
        return False
    
    print(f"Found core_hook.c at: {core_hook}")
    
    with open(core_hook, 'r') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Pattern 1: Fix umount(pathname) in ksu_umount_mnt function
    # Replace with sys_umount syscall
    # The pattern is: err = umount(pathname);
    if 'err = umount(pathname);' in content:
        content = content.replace(
            'err = umount(pathname);',
            'err = sys_umount(pathname, MNT_DETACH);'
        )
        changes.append("Fixed umount(pathname) -> sys_umount(pathname, MNT_DETACH)")
    
    # Pattern 2: Fix return umount(...) patterns
    pattern_return = r'return\s+umount\s*\('
    if re.search(pattern_return, content):
        content = re.sub(
            r'return\s+umount\s*\(([^)]+)\)',
            r'return sys_umount(\1, MNT_DETACH)',
            content
        )
        changes.append("Fixed return umount(...) -> return sys_umount(..., MNT_DETACH)")
    
    # Pattern 3: Fix standalone umount calls (not returns)
    pattern_standalone = r'\bumount\s*\('
    if re.search(pattern_standalone, content) and 'sys_umount' not in content:
        content = re.sub(r'\bumount\s*\(', 'sys_umount(', content)
        changes.append("Fixed umount() -> sys_umount()")
    
    # Add sys_umount declaration if not present
    # In kernel 4.9, sys_umount is declared in linux/syscalls.h or we need to declare it
    if 'sys_umount' in content and 'asmlinkage long sys_umount' not in content:
        # Add declaration after the last #include
        lines = content.split('\n')
        last_include_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('#include'):
                last_include_idx = i
        
        if last_include_idx >= 0:
            # Check if syscalls.h is already included
            has_syscalls = any('syscalls.h' in line for line in lines)
            if not has_syscalls:
                lines.insert(last_include_idx + 1, '#include <linux/syscalls.h>')
                changes.append("Added #include <linux/syscalls.h>")
            
            # Add sys_umount declaration for kernel 4.9
            declaration = '/* Kernel 4.9 compatibility: sys_umount declaration */'
            if declaration not in content:
                lines.insert(last_include_idx + 2, declaration)
                lines.insert(last_include_idx + 3, 'asmlinkage long sys_umount(const char __user *name, int flags);')
                changes.append("Added sys_umount declaration")
            
            content = '\n'.join(lines)
    
    # Write back if changes were made
    if content != original_content:
        with open(core_hook, 'w') as f:
            f.write(content)
        print(f"SUCCESS: Fixed {core_hook}")
        for change in changes:
            print(f"  - {change}")
        return True
    else:
        print(f"No changes needed for {core_hook}")
        # Even if no changes, let's show what we're looking for
        if 'umount(' in content and 'sys_umount' not in content:
            print("WARNING: Found umount() calls that weren't fixed!")
            # Find and display them
            for i, line in enumerate(content.split('\n'), 1):
                if 'umount(' in line and 'sys_umount' not in line and 'ksu_umount' not in line:
                    print(f"  Line {i}: {line.strip()}")
        return False


def main():
    if len(sys.argv) < 2:
        kernel_dir = os.environ.get('KERNEL_DIR', '.')
    else:
        kernel_dir = sys.argv[1]
    
    print("=" * 60)
    print("KernelSU-Next 4.9 Compatibility Fix v35")
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
        print("WARNING: No fixes applied")
    print("=" * 60)
    
    return 0 if fixed else 1


if __name__ == '__main__':
    sys.exit(main())
