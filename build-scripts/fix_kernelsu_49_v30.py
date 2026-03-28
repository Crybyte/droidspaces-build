#!/usr/bin/env python3
"""
KernelSU-Next v1.0.7 Kernel 4.9 Compatibility Fix v30
ULTRA-AGGRESSIVE: Direct line-by-line patching for the 'flags' undeclared error

This script takes a completely different approach - it reads the file line by line
and makes direct string replacements without complex regex.
"""

import sys
import os
import re

def fix_core_hook_c(filepath):
    """Fix core_hook.c with ultra-aggressive line-by-line patching"""
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    original_lines = lines[:]
    fixes = []
    
    # Process each line
    for i, line in enumerate(lines):
        line_num = i + 1
        
        # ULTRA-AGGRESSIVE FIX 1: Replace ANY occurrence of ksu_umount_mnt with flags variable
        # Pattern: ksu_umount_mnt(&path, flags) -> ksu_umount_mnt(&path, 0)
        if 'ksu_umount_mnt' in line and 'flags' in line:
            # Multiple strategies to ensure we catch all variations
            
            # Strategy A: Direct string replacement (most reliable)
            if 'ksu_umount_mnt(&path, flags)' in line:
                lines[i] = line.replace('ksu_umount_mnt(&path, flags)', 'ksu_umount_mnt(&path, 0)')
                fixes.append(f"Line {line_num}: Direct replacement of ksu_umount_mnt(&path, flags)")
            
            # Strategy B: Variable whitespace
            elif re.search(r'ksu_umount_mnt\s*\(\s*&path\s*,\s*flags\s*\)', line):
                lines[i] = re.sub(r'ksu_umount_mnt\s*\(\s*&path\s*,\s*flags\s*\)', 'ksu_umount_mnt(&path, 0)', line)
                fixes.append(f"Line {line_num}: Regex replacement of ksu_umount_mnt with &path, flags")
            
            # Strategy C: Generic flags variable (any first param)
            elif re.search(r'ksu_umount_mnt\s*\([^,]+,\s*flags\s*\)', line):
                lines[i] = re.sub(r'(ksu_umount_mnt\s*\()([^,]+)(,\s*)flags(\s*\))', r'\1\2\30\4', line)
                fixes.append(f"Line {line_num}: Generic flags replacement in ksu_umount_mnt")
        
        # ULTRA-AGGRESSIVE FIX 2: Fix try_umount function definition
        # Change: static void try_umount(const char *mnt, bool check_mnt, int flags)
        # To:     static void try_umount(const char *mnt, bool check_mnt)
        if line_num <= 600 and 'try_umount' in line and 'int flags' in line:
            if 'static void try_umount(const char *mnt, bool check_mnt, int flags)' in line:
                lines[i] = line.replace(
                    'static void try_umount(const char *mnt, bool check_mnt, int flags)',
                    'static void try_umount(const char *mnt, bool check_mnt)'
                )
                fixes.append(f"Line {line_num}: Fixed try_umount definition (removed int flags)")
        
        # ULTRA-AGGRESSIVE FIX 3: Fix try_umount 3-argument calls
        # Pattern: try_umount(something, something, flags) -> try_umount(something, something)
        if 'try_umount(' in line and line.count(',') >= 2:
            # Check if this is a call with 3 arguments
            match = re.search(r'try_umount\s*\(([^,]+),\s*([^,]+),\s*([^)]+)\)', line)
            if match:
                # Replace with 2 arguments
                lines[i] = re.sub(r'try_umount\s*\(([^,]+),\s*([^,]+),\s*([^)]+)\)', r'try_umount(\1, \2)', line)
                fixes.append(f"Line {line_num}: Removed third argument from try_umount call")
    
    # Write the fixed content back
    if lines != original_lines:
        with open(filepath, 'w') as f:
            f.writelines(lines)
        print(f"\nApplied {len(fixes)} fixes to {filepath}:")
        for fix in fixes:
            print(f"  - {fix}")
        return True
    else:
        print(f"\nNo changes made to {filepath}")
        return False

def verify_fix(filepath):
    """Verify that the fixes were actually applied"""
    print("\n=== Verification ===")
    
    with open(filepath, 'r') as f:
        content = f.read()
        lines = f.readlines()
    
    issues = []
    
    # Check for remaining ksu_umount_mnt with flags variable
    ksu_flags_pattern = re.findall(r'ksu_umount_mnt\s*\([^)]*flags[^)]*\)', content)
    if ksu_flags_pattern:
        issues.append(f"Found {len(ksu_flags_pattern)} ksu_umount_mnt calls with 'flags'")
        for match in ksu_flags_pattern[:3]:
            issues.append(f"  -> {match}")
    
    # Check for try_umount with 3 arguments
    try_umount_3arg = re.findall(r'try_umount\s*\([^,]+,[^,]+,[^)]+\)', content)
    if try_umount_3arg:
        issues.append(f"Found {len(try_umount_3arg)} try_umount calls with 3 arguments")
    
    # Check try_umount definition
    if 'static void try_umount(const char *mnt, bool check_mnt, int flags)' in content:
        issues.append("try_umount definition still has 3 parameters")
    
    # Show line 591 specifically
    with open(filepath, 'r') as f:
        all_lines = f.readlines()
        if len(all_lines) >= 591:
            print(f"\nLine 591: {all_lines[590].rstrip()}")
            if 'flags' in all_lines[590] and 'ksu_umount_mnt' in all_lines[590]:
                issues.append("Line 591 still has flags variable!")
    
    if issues:
        print("\nWARNING: Remaining issues detected:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("SUCCESS: All kernel 4.9 compatibility issues fixed!")
        return True

def main():
    # Get the KSU kernel directory from environment or argument
    ksu_dir = os.environ.get('KSU_DIR', '')
    if not ksu_dir and len(sys.argv) > 1:
        ksu_dir = sys.argv[1]
    
    if not ksu_dir:
        print("Error: KSU directory not specified")
        print("Usage: KSU_DIR=/path/to/kernelsu/kernel python3 fix_kernelsu_49_v30.py")
        sys.exit(1)
    
    core_hook_path = os.path.join(ksu_dir, 'core_hook.c')
    
    if not os.path.exists(core_hook_path):
        print(f"Error: core_hook.c not found at {core_hook_path}")
        sys.exit(1)
    
    print(f"KernelSU-Next v1.0.7 Kernel 4.9 Compatibility Fix v30 (ULTRA-AGGRESSIVE)")
    print(f"Target: {core_hook_path}")
    
    # Create backup
    backup_path = core_hook_path + '.v30.bak'
    with open(core_hook_path, 'r') as f:
        original_content = f.read()
    with open(backup_path, 'w') as f:
        f.write(original_content)
    print(f"Backup created: {backup_path}")
    
    # Apply fixes
    fixed = fix_core_hook_c(core_hook_path)
    
    # Verify the fixes
    success = verify_fix(core_hook_path)
    
    if not success:
        print("\n!!! WARNING: Fix verification failed - build may still fail !!!")
        sys.exit(1)
    
    sys.exit(0)

if __name__ == '__main__':
    main()
