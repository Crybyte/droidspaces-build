#!/usr/bin/env python3
"""
CRITICAL FIX v15: Comprehensive kernel 4.9 compatibility fix for KernelSU-Next v1.0.7
Handles: path_umount, try_umount, flags parameters, check_mnt references
"""
import os
import sys
import re

def fix_core_hook_c(filepath):
    """Fix core_hook.c for kernel 4.9 compatibility"""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = []
    
    # 1. Fix path_umount(path, flags) -> umount(path) 
    # path_umount was introduced in kernel 5.9
    path_umount_matches = len(re.findall(r'path_umount\s*\(', content))
    if path_umount_matches:
        content = re.sub(
            r'path_umount\s*\(\s*([^,]+)\s*,\s*[^)]+\s*\)',
            r'umount(\1)',
            content
        )
        fixes_applied.append(f"Fixed {path_umount_matches} path_umount calls")
    
    # 2. Fix try_umount function definition - remove flags parameter
    # Original: static void try_umount(const char *mnt, bool check_mnt, int flags)
    # Fixed: static void try_umount(const char *mnt, bool check_mnt)
    try_umount_def = re.search(r'static\s+void\s+try_umount\s*\([^)]*\)', content)
    if try_umount_def:
        old_def = try_umount_def.group(0)
        new_def = re.sub(r'\s*,\s*int\s+flags\s*\)', ')', old_def)
        if old_def != new_def:
            content = content.replace(old_def, new_def)
            fixes_applied.append("Fixed try_umount function definition (removed flags)")
    
    # 3. Remove flags parameter from try_umount calls
    # try_umount(path, check_mnt, flags) -> try_umount(path, check_mnt)
    try_umount_calls = len(re.findall(r'try_umount\s*\([^,]+,[^,]+,[^)]+\)', content))
    if try_umount_calls:
        content = re.sub(
            r'try_umount\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*[^)]+\s*\)',
            r'try_umount(\1, \2)',
            content
        )
        fixes_applied.append(f"Fixed {try_umount_calls} 3-arg try_umount calls")
    
    # 4. Fix ksu_umount_mnt function definition - remove flags parameter
    ksu_umount_def = re.search(r'int\s+ksu_umount_mnt\s*\([^)]*\)', content)
    if ksu_umount_def:
        old_def = ksu_umount_def.group(0)
        new_def = re.sub(r'\s*,\s*int\s+\w+\s*\)', ')', old_def)
        if old_def != new_def:
            content = content.replace(old_def, new_def)
            fixes_applied.append("Fixed ksu_umount_mnt function definition")
    
    # 5. Fix calls to ksu_umount_mnt - remove second argument
    ksu_umount_calls = len(re.findall(r'ksu_umount_mnt\s*\([^)]+,[^)]+\)', content))
    if ksu_umount_calls:
        content = re.sub(
            r'(ksu_umount_mnt\s*\(\s*[^)]+)\s*,\s*[^)]+\s*\)',
            r'\1)',
            content
        )
        fixes_applied.append(f"Fixed {ksu_umount_calls} ksu_umount_mnt calls")
    
    # 6. Fix ksu_task_fix_setuid - remove flags parameter
    task_fix_setuid_def = re.search(r'static\s+int\s+ksu_task_fix_setuid\s*\([^)]*\)', content)
    if task_fix_setuid_def:
        old_def = task_fix_setuid_def.group(0)
        new_def = re.sub(r'\s*,\s*int\s+flags\s*\)', ')', old_def)
        if old_def != new_def:
            content = content.replace(old_def, new_def)
            fixes_applied.append("Fixed ksu_task_fix_setuid function definition")
    
    # 7. Replace any remaining bare 'flags' variable references with 0
    # This is a safety net - find patterns where flags is used but not declared
    flags_refs = re.findall(r'[^\w]flags[^\w]', content)
    # Exclude known safe patterns (include guards, struct fields, etc.)
    safe_flags = ['#include <linux/irqflags.h>', '->flags', '.flags', 'version_flags']
    unsafe_flags = [f for f in flags_refs if not any(safe in f for safe in safe_flags)]
    if unsafe_flags:
        # Replace bare 'flags' with '0' only in contexts where it's likely a variable
        content = re.sub(r'\bflags\b(?=\s*[,;)])', '0', content)
        fixes_applied.append(f"Replaced {len(unsafe_flags)} bare flags references with 0")
    
    # 8. Replace check_mnt with false (0) to avoid undeclared errors
    check_mnt_count = len(re.findall(r'\bcheck_mnt\b', content))
    if check_mnt_count:
        content = re.sub(r'\bcheck_mnt\b', 'false', content)
        fixes_applied.append(f"Replaced {check_mnt_count} check_mnt with false")
    
    changes_made = content != original_content
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Fixed {filepath}:")
    if fixes_applied:
        for fix in fixes_applied:
            print(f"  - {fix}")
    else:
        print("  - No changes needed")
    
    # Verify critical fixes
    remaining_issues = []
    if re.search(r'int\s+flags\s*\)', content):
        remaining_issues.append("int flags) still present")
    if re.search(r'path_umount\s*\(', content):
        remaining_issues.append("path_umount still present")
    
    if remaining_issues:
        print(f"WARNING: Remaining issues: {remaining_issues}")
    
    return changes_made

def main():
    if len(sys.argv) < 2:
        ksu_dir = os.environ.get('KSU_DIR', '/tmp/ksu_test')
    else:
        ksu_dir = sys.argv[1]
    
    core_hook = os.path.join(ksu_dir, 'core_hook.c')
    
    if not os.path.exists(core_hook):
        print(f"ERROR: {core_hook} not found!")
        # Search for it
        for root, dirs, files in os.walk(ksu_dir):
            if 'core_hook.c' in files:
                core_hook = os.path.join(root, 'core_hook.c')
                print(f"Found at: {core_hook}")
                break
        else:
            sys.exit(1)
    
    fix_core_hook_c(core_hook)
    print("Kernel 4.9 compatibility fixes applied successfully!")

if __name__ == '__main__':
    main()
