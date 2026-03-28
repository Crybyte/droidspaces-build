#!/usr/bin/env python3
"""
Kernel 4.9 compatibility fix for KernelSU-Next v1.0.7 - v42
CRITICAL FIX: Direct fix for line 131 current_thread_info()->0 syntax error
This runs AFTER the pre-patched file is applied to fix any remaining issues.
"""

import sys
import os
import re

def fix_line_131_direct(filepath):
    """
    Direct fix for line 131 in disable_seccomp function.
    The pre-patched file has: current_thread_info()->0 which is invalid syntax.
    Should be: current_thread_info()->flags
    """
    print(f"Processing: {filepath}")
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    if len(lines) < 131:
        print(f"ERROR: File has only {len(lines)} lines, expected at least 131")
        return False
    
    # Show line 131 before fix
    print(f"Line 131 BEFORE: {lines[130].rstrip()}")
    
    changes = []
    
    # Fix line 131 specifically (disable_seccomp function)
    if 'current_thread_info()->0' in lines[130]:
        lines[130] = lines[130].replace('current_thread_info()->0', 'current_thread_info()->flags')
        changes.append("Fixed line 131: current_thread_info()->0 -> current_thread_info()->flags")
    
    # Also fix any other occurrences in the file
    for i in range(len(lines)):
        if 'current_thread_info()->0' in lines[i]:
            lines[i] = lines[i].replace('current_thread_info()->0', 'current_thread_info()->flags')
            changes.append(f"Fixed line {i+1}: current_thread_info()->0 -> current_thread_info()->flags")
        if 'current_thread_info()->1' in lines[i]:
            lines[i] = lines[i].replace('current_thread_info()->1', 'current_thread_info()->work')
            changes.append(f"Fixed line {i+1}: current_thread_info()->1 -> current_thread_info()->work")
    
    # Write back
    with open(filepath, 'w') as f:
        f.writelines(lines)
    
    # Show line 131 after fix
    print(f"Line 131 AFTER: {lines[130].rstrip()}")
    
    if changes:
        print(f"Made {len(changes)} changes:")
        for c in changes:
            print(f"  - {c}")
    else:
        print("No changes needed")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: fix_kernelsu_49_v42.py <kernel_directory>")
        sys.exit(1)
    
    kernel_dir = sys.argv[1]
    
    # Find core_hook.c
    core_hook_path = os.path.join(kernel_dir, 'drivers', 'kernelsu', 'core_hook.c')
    
    # Check if it's a symlink
    if os.path.islink(core_hook_path):
        real_path = os.readlink(core_hook_path)
        if not os.path.isabs(real_path):
            real_path = os.path.join(os.path.dirname(core_hook_path), real_path)
        core_hook_path = os.path.normpath(real_path)
        print(f"Resolved symlink to: {core_hook_path}")
    
    if not os.path.exists(core_hook_path):
        print(f"ERROR: core_hook.c not found at {core_hook_path}")
        # Try alternative locations
        for alt in ['KernelSU/kernel/core_hook.c', 'KernelSU-Next/kernel/core_hook.c']:
            alt_path = os.path.join(kernel_dir, alt)
            if os.path.exists(alt_path):
                core_hook_path = alt_path
                print(f"Using alternative: {core_hook_path}")
                break
        else:
            print("ERROR: Could not find core_hook.c")
            sys.exit(1)
    
    print(f"Found core_hook.c: {core_hook_path}")
    
    # Apply the fix
    if fix_line_131_direct(core_hook_path):
        print("\n=== Verification ===")
        with open(core_hook_path, 'r') as f:
            lines = f.readlines()
            print(f"Final line 131: {lines[130].rstrip()}")
            
        # Check for any remaining issues
        with open(core_hook_path, 'r') as f:
            content = f.read()
            if 'current_thread_info()->0' in content:
                print("WARNING: File still contains current_thread_info()->0")
                sys.exit(1)
            else:
                print("SUCCESS: All current_thread_info()->0 fixed")
    else:
        print("ERROR: Fix failed")
        sys.exit(1)

if __name__ == '__main__':
    main()
