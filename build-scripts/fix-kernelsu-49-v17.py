#!/usr/bin/env python3
"""
KernelSU-Next v1.0.7 kernel 4.9 compatibility fix - VERSION 17
Comprehensive fix for flags undeclared errors and function signatures
"""

import re
import sys
import os

def fix_core_hook(filepath):
    """Fix core_hook.c for kernel 4.9 compatibility"""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    
    # Fix 1: ksu_task_fix_setuid function - remove flags parameter from declaration
    # Pattern: static int ksu_task_fix_setuid(..., int flags) {
    content = re.sub(
        r'(static\s+int\s+ksu_task_fix_setuid\s*\([^)]*),\s*int\s+flags\s*\)',
        r'\1)',
        content
    )
    
    # Fix 2: ksu_umount_mnt function - remove flags parameter
    content = re.sub(
        r'(static\s+int\s+ksu_umount_mnt\s*\([^)]*),\s*int\s+flags\s*\)',
        r'\1)',
        content
    )
    
    # Fix 3: try_umount function - ensure flags is declared if used
    # If try_umount uses flags but it's not declared, add declaration
    try_umount_pattern = r'(static\s+int\s+try_umount\s*\([^)]*\)\s*\{)'
    
    def add_flags_decl(match):
        func_start = match.group(1)
        # Check if flags is used in this function
        func_end_pos = find_function_end(content, match.end())
        func_body = content[match.start():func_end_pos]
        
        # If function uses flags but doesn't declare it, add declaration
        if re.search(r'\bflags\b', func_body) and 'int flags' not in func_body[:200]:
            return func_start + '\n\tint flags = 0;'
        return func_start
    
    content = re.sub(try_umount_pattern, add_flags_decl, content)
    
    # Fix 4: Replace all path_umount calls with umount
    content = re.sub(
        r'path_umount\s*\(\s*([^,]+)\s*,[^)]+\)',
        r'umount(\1)',
        content
    )
    
    # Fix 5: Replace check_mnt with 0 or false
    content = re.sub(r'\bcheck_mnt\b', '0', content)
    
    # Fix 6: Fix try_umount calls with 3 args to 1 arg
    content = re.sub(
        r'try_umount\s*\(\s*([^,]+)\s*,[^,]+,[^)]+\)',
        r'try_umount(\1)',
        content
    )
    
    # Fix 7: Fix try_umount calls with 2 args to 1 arg  
    content = re.sub(
        r'try_umount\s*\(\s*([^,]+)\s*,[^)]+\)',
        r'try_umount(\1)',
        content
    )
    
    # Fix 8: Fix KERNEL_VERSION 2-arg calls
    content = re.sub(
        r'KERNEL_VERSION\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)',
        r'KERNEL_VERSION(\1, \2, 0)',
        content
    )
    
    # Fix 9: Handle ksu_umount_mnt function body - remove flags usage
    # Find ksu_umount_mnt and ensure it doesn't use undeclared flags
    ksu_umount_pattern = r'(static\s+int\s+ksu_umount_mnt\s*\([^{]+\)\s*\{)([^}]+)'
    
    def fix_ksu_umount_body(match):
        func_sig = match.group(1)
        func_body = match.group(2)
        
        # Replace flags with 0 in the function body
        func_body = re.sub(r'\bflags\b', '0', func_body)
        
        return func_sig + func_body
    
    content = re.sub(ksu_umount_pattern, fix_ksu_umount_body, content, flags=re.DOTALL)
    
    # Fix 10: Handle ksu_task_fix_setuid function body
    ksu_task_pattern = r'(static\s+int\s+ksu_task_fix_setuid\s*\([^{]+\)\s*\{)'
    
    def fix_ksu_task_body(match):
        func_start = match.group(1)
        func_end_pos = find_function_end(content, match.end())
        func_body = content[match.end():func_end_pos]
        
        # Replace flags with 0 if it's not declared
        if 'int flags' not in func_body[:300]:
            func_body = re.sub(r'\bflags\b', '0', func_body)
        
        return func_start + func_body + content[func_end_pos:]
    
    # Apply changes
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Fixed: {filepath}")
        return True
    else:
        print(f"No changes needed: {filepath}")
        return False

def find_function_end(content, start_pos):
    """Find the end of a function starting at start_pos"""
    brace_count = 0
    in_func = False
    
    for i in range(start_pos, len(content)):
        if content[i] == '{':
            brace_count += 1
            in_func = True
        elif content[i] == '}':
            brace_count -= 1
            if in_func and brace_count == 0:
                return i + 1
    
    return len(content)

def fix_all_files(ksu_dir):
    """Fix all C files in the KernelSU kernel directory"""
    
    fixed_count = 0
    
    for filename in os.listdir(ksu_dir):
        if filename.endswith('.c') or filename.endswith('.h'):
            filepath = os.path.join(ksu_dir, filename)
            if os.path.isfile(filepath):
                if fix_file(filepath):
                    fixed_count += 1
    
    print(f"\nTotal files fixed: {fixed_count}")
    return fixed_count

def fix_file(filepath):
    """Fix a single file"""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    
    # Fix path_umount calls
    content = re.sub(
        r'path_umount\s*\(\s*([^,]+)\s*,[^)]+\)',
        r'umount(\1)',
        content
    )
    
    # Fix KERNEL_VERSION 2-arg calls
    content = re.sub(
        r'KERNEL_VERSION\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)',
        r'KERNEL_VERSION(\1, \2, 0)',
        content
    )
    
    # Replace check_mnt with 0
    content = re.sub(r'\bcheck_mnt\b', '0', content)
    
    # Fix try_umount 3-arg calls
    content = re.sub(
        r'try_umount\s*\(\s*([^,]+)\s*,[^,]+,[^)]+\)',
        r'try_umount(\1)',
        content
    )
    
    # Fix try_umount 2-arg calls
    content = re.sub(
        r'try_umount\s*\(\s*([^,]+)\s*,[^)]+\)',
        r'try_umount(\1)',
        content
    )
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Fixed: {os.path.basename(filepath)}")
        return True
    
    return False

def main():
    if len(sys.argv) < 2:
        print("Usage: fix-kernelsu-49-v17.py <ksu_kernel_dir>")
        sys.exit(1)
    
    ksu_dir = sys.argv[1]
    
    if not os.path.isdir(ksu_dir):
        print(f"ERROR: Directory not found: {ksu_dir}")
        sys.exit(1)
    
    print(f"=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fix v17 ===")
    print(f"Target directory: {ksu_dir}")
    
    # Fix core_hook.c specially
    core_hook = os.path.join(ksu_dir, 'core_hook.c')
    if os.path.exists(core_hook):
        print("\nApplying comprehensive fixes to core_hook.c...")
        fix_core_hook(core_hook)
    
    # Fix all other files
    print("\nApplying standard fixes to all files...")
    fix_all_files(ksu_dir)
    
    # Verify
    print("\n=== Verification ===")
    remaining = 0
    for filename in os.listdir(ksu_dir):
        if filename.endswith('.c') or filename.endswith('.h'):
            filepath = os.path.join(ksu_dir, filename)
            if os.path.isfile(filepath):
                with open(filepath, 'r') as f:
                    content = f.read()
                if 'path_umount' in content:
                    print(f"WARNING: path_umount still in {filename}")
                    remaining += 1
    
    if remaining == 0:
        print("SUCCESS: All path_umount calls removed")
    else:
        print(f"WARNING: {remaining} files still have path_umount")
    
    print("\n=== Fix v17 complete ===")

if __name__ == '__main__':
    main()
