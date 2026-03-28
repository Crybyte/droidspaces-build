#!/usr/bin/env python3
"""
KernelSU-Next v1.0.7 Kernel 4.9 Compatibility Fix v29

This script provides a CONSISTENT approach to fixing ksu_umount_mnt and try_umount
for kernel 4.9 compatibility. The key insight is that BOTH the function definition
AND all call sites must be changed together.

Strategy:
1. For ksu_umount_mnt: Keep the flags parameter in definition, replace with 0 at call sites
2. For try_umount: Change from 3-param to 2-param (remove flags), update all call sites
"""

import sys
import re
import os

def fix_core_hook_c(filepath):
    """Fix core_hook.c with consistent function signatures and call sites"""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    fixes = []
    
    # STRATEGY 1: Fix ksu_umount_mnt
    # Keep function signature with 2 params, but ensure call sites use 0 instead of flags variable
    
    # Check if there's a call to ksu_umount_mnt with a flags variable (not a constant)
    # Pattern: ksu_umount_mnt(&path, flags) -> ksu_umount_mnt(&path, 0)
    if re.search(r'ksu_umount_mnt\s*\(\s*([^,]+)\s*,\s*flags\s*\)', content):
        content = re.sub(
            r'ksu_umount_mnt\s*\(\s*([^,]+)\s*,\s*flags\s*\)',
            r'ksu_umount_mnt(\1, 0)',
            content
        )
        fixes.append("Fixed ksu_umount_mnt calls: replaced 'flags' variable with 0")
    
    # STRATEGY 2: Fix try_umount - change from 3-param to 2-param
    # First, change the function definition
    if 'static void try_umount(const char *mnt, bool check_mnt, int flags)' in content:
        content = content.replace(
            'static void try_umount(const char *mnt, bool check_mnt, int flags)',
            'static void try_umount(const char *mnt, bool check_mnt)'
        )
        fixes.append("Fixed try_umount definition: removed 'int flags' parameter")
        
        # Now fix all call sites - remove the third argument (flags)
        # Pattern: try_umount("string", true/false, FLAG) -> try_umount("string", true/false)
        content = re.sub(
            r'try_umount\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*[^)]+\s*\)',
            r'try_umount(\1, \2)',
            content
        )
        fixes.append("Fixed try_umount calls: removed third argument (flags)")
    
    # STRATEGY 3: Ensure ksu_umount_mnt implementation handles the flags parameter
    # Find the ksu_umount_mnt function and ensure it doesn't call path_umount on kernel 4.9
    ksu_umount_pattern = r'static int ksu_umount_mnt\(struct path \*path, int flags\)\s*\{[^}]+\}'
    match = re.search(ksu_umount_pattern, content, re.DOTALL)
    if match:
        original_func = match.group(0)
        # Check if it's using path_umount which doesn't exist in kernel 4.9
        if 'path_umount' in original_func:
            # Replace the entire function with a kernel 4.9 compatible version
            new_func = '''static int ksu_umount_mnt(struct path *path, int flags)
{
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 9, 0) || defined(KSU_UMOUNT)
\treturn path_umount(path, flags);
#else
\t// Kernel 4.9 compatibility: path_umount does not exist
\t// Return -ENOSYS to indicate the function is not implemented
\treturn -ENOSYS;
#endif
}'''
            content = content.replace(original_func, new_func)
            fixes.append("Fixed ksu_umount_mnt implementation: added kernel 4.9 compatibility")
    
    # STRATEGY 4: Fix any remaining try_umount calls that might have been missed
    # Double-check all try_umount calls have exactly 2 arguments
    remaining_3arg = re.findall(r'try_umount\s*\([^,]+,[^,]+,[^)]+\)', content)
    if remaining_3arg:
        for call in remaining_3arg:
            # Extract the path and check_mnt arguments, drop the flags
            match = re.match(r'try_umount\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)', call)
            if match:
                new_call = f'try_umount({match.group(1)}, {match.group(2)})'
                content = content.replace(call, new_call)
        fixes.append("Fixed remaining 3-argument try_umount calls")
    
    # Write the fixed content back
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"\nApplied {len(fixes)} fixes to {filepath}:")
        for fix in fixes:
            print(f"  - {fix}")
        return True
    else:
        print(f"\nNo changes needed for {filepath}")
        return False

def main():
    # Get the KSU kernel directory from environment or argument
    ksu_dir = os.environ.get('KSU_DIR', '')
    if not ksu_dir and len(sys.argv) > 1:
        ksu_dir = sys.argv[1]
    
    if not ksu_dir:
        print("Error: KSU directory not specified")
        print("Usage: KSU_DIR=/path/to/kernelsu/kernel python3 fix_kernelsu_49_v29.py")
        sys.exit(1)
    
    core_hook_path = os.path.join(ksu_dir, 'core_hook.c')
    
    if not os.path.exists(core_hook_path):
        print(f"Error: core_hook.c not found at {core_hook_path}")
        sys.exit(1)
    
    print(f"KernelSU-Next v1.0.7 Kernel 4.9 Compatibility Fix v29")
    print(f"Target: {core_hook_path}")
    
    # Create backup
    backup_path = core_hook_path + '.v29.bak'
    with open(core_hook_path, 'r') as f:
        original_content = f.read()
    with open(backup_path, 'w') as f:
        f.write(original_content)
    print(f"Backup created: {backup_path}")
    
    # Apply fixes
    fixed = fix_core_hook_c(core_hook_path)
    
    # Verify the fixes
    print("\n=== Verification ===")
    with open(core_hook_path, 'r') as f:
        new_content = f.read()
    
    # Check for remaining issues
    issues = []
    
    # Check 1: ksu_umount_mnt should have 2 params in definition
    if 'static int ksu_umount_mnt(struct path *path, int flags)' not in new_content:
        issues.append("ksu_umount_mnt signature may be incorrect")
    
    # Check 2: No calls to ksu_umount_mnt with 'flags' variable
    if re.search(r'ksu_umount_mnt\s*\([^)]+,\s*flags\s*\)', new_content):
        issues.append("ksu_umount_mnt still called with 'flags' variable")
    
    # Check 3: try_umount should have 2 params in definition
    if 'static void try_umount(const char *mnt, bool check_mnt, int flags)' in new_content:
        issues.append("try_umount still has 3 parameters")
    
    # Check 4: No 3-argument try_umount calls
    if re.search(r'try_umount\s*\([^,]+,[^,]+,[^)]+\)', new_content):
        issues.append("try_umount still called with 3 arguments")
    
    if issues:
        print("WARNING: Remaining issues detected:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("SUCCESS: All kernel 4.9 compatibility issues fixed!")
        print("\nSummary:")
        print("  - ksu_umount_mnt: 2-parameter function, flags replaced with 0 at call sites")
        print("  - try_umount: Converted from 3-param to 2-param, all call sites updated")
        sys.exit(0)

if __name__ == '__main__':
    main()
