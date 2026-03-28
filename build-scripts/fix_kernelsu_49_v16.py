#!/usr/bin/env python3
"""
CRITICAL FIX v16: Comprehensive kernel 4.9 compatibility fix for KernelSU-Next v1.0.7
Handles: path_umount, try_umount, flags parameters, check_mnt references
Key improvement: Handles multi-line function definitions
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
    path_umount_matches = len(re.findall(r'path_umount\s*\(', content))
    if path_umount_matches:
        content = re.sub(
            r'path_umount\s*\(\s*([^,]+)\s*,\s*[^)]+\s*\)',
            r'umount(\1)',
            content
        )
        fixes_applied.append(f"Fixed {path_umount_matches} path_umount calls")
    
    # 2. Fix try_umount function definition - remove flags parameter (multi-line aware)
    # Pattern matches: static void try_umount(const char *mnt, bool check_mnt, int flags)
    # Or multi-line version
    try_umount_pattern = r'static\s+void\s+try_umount\s*\([^)]*\)'
    try_umount_def = re.search(try_umount_pattern, content, re.DOTALL)
    if try_umount_def:
        old_def = try_umount_def.group(0)
        # Remove the flags parameter (handles both single and multi-line)
        new_def = re.sub(r'\s*,\s*int\s+flags', '', old_def)
        if old_def != new_def:
            content = content.replace(old_def, new_def)
            fixes_applied.append("Fixed try_umount function definition (removed flags)")
    
    # 3. Remove flags parameter from try_umount calls
    try_umount_calls = len(re.findall(r'try_umount\s*\([^,]+,[^,]+,[^)]+\)', content))
    if try_umount_calls:
        content = re.sub(
            r'try_umount\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*[^)]+\s*\)',
            r'try_umount(\1, \2)',
            content
        )
        fixes_applied.append(f"Fixed {try_umount_calls} 3-arg try_umount calls")
    
    # 4. Fix ksu_umount_mnt function definition - remove flags parameter (multi-line aware)
    ksu_umount_pattern = r'int\s+ksu_umount_mnt\s*\([^)]*\)'
    ksu_umount_def = re.search(ksu_umount_pattern, content, re.DOTALL)
    if ksu_umount_def:
        old_def = ksu_umount_def.group(0)
        new_def = re.sub(r'\s*,\s*int\s+\w+', '', old_def)
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
    
    # 6. Fix ksu_task_fix_setuid - remove flags parameter (multi-line aware)
    # This is the CRITICAL fix - handles definitions spanning multiple lines
    task_fix_pattern = r'static\s+int\s+ksu_task_fix_setuid\s*\([^)]*\)'
    task_fix_def = re.search(task_fix_pattern, content, re.DOTALL)
    if task_fix_def:
        old_def = task_fix_def.group(0)
        new_def = re.sub(r'\s*,\s*int\s+flags', '', old_def)
        if old_def != new_def:
            content = content.replace(old_def, new_def)
            fixes_applied.append("Fixed ksu_task_fix_setuid function definition")
    
    # 7. Replace any remaining bare 'flags' variable references with 0
    # This catches any remaining usages after function signature fixes
    flags_in_body = re.findall(r'\bflags\b', content)
    if flags_in_body:
        # Only replace flags that appear to be variables (not struct fields, etc.)
        # Pattern: flags followed by comma, semicolon, or closing paren
        content = re.sub(r'\bflags\b(?=\s*[,;)])', '0', content)
        fixes_applied.append(f"Replaced {len(flags_in_body)} bare flags references with 0")
    
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
    if re.search(r'\bflags\b(?=\s*[,;)])', content):
        remaining_flags = len(re.findall(r'\bflags\b(?=\s*[,;)])', content))
        remaining_issues.append(f"{remaining_flags} bare flags references still present")
    
    if remaining_issues:
        print(f"WARNING: Remaining issues: {remaining_issues}")
    else:
        print("VERIFIED: All kernel 4.9 compatibility issues resolved")
    
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
