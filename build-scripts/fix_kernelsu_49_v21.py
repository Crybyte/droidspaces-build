#!/usr/bin/env python3
"""
CRITICAL FIX v21: Fixed ksu_umount_mnt call handling
The v18 fixer had a regex that corrupted ksu_umount_mnt(&path, flags) calls
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
    
    # 2. Fix try_umount function definition - remove extra params
    content = re.sub(
        r'static\s+void\s+try_umount\s*\(\s*const\s+char\s+\*\s*\w+\s*,[^)]+\)',
        r'static void try_umount(const char *mnt)',
        content
    )
    fixes_applied.append("Fixed try_umount function signature")
    
    # 3. Fix try_umount calls - reduce to single arg
    content = re.sub(
        r'try_umount\s*\(\s*([^,)]+)\s*,[^)]+\)',
        r'try_umount(\1)',
        content
    )
    fixes_applied.append("Fixed try_umount calls")
    
    # 4. CRITICAL FIX v21: Fix ksu_umount_mnt calls properly
    # The v18 fixer had a broken regex that could corrupt the file
    # Pattern: ksu_umount_mnt(&path, flags) -> ksu_umount_mnt(&path)
    ksu_calls = len(re.findall(r'ksu_umount_mnt\s*\(', content))
    if ksu_calls:
        # Use a simpler, more reliable approach
        # Match the function call and capture the first argument
        def fix_ksu_call(match):
            full_call = match.group(0)
            # Extract first argument (should be &path or similar)
            arg_match = re.search(r'ksu_umount_mnt\s*\(\s*([^,\s]+)', full_call)
            if arg_match:
                first_arg = arg_match.group(1)
                return f'ksu_umount_mnt({first_arg})'
            return full_call
        
        content = re.sub(r'ksu_umount_mnt\s*\([^)]+\)', fix_ksu_call, content)
        fixes_applied.append(f"Fixed {ksu_calls} ksu_umount_mnt calls")
    
    # 5. Fix ksu_umount_mnt function definition
    content = re.sub(
        r'int\s+ksu_umount_mnt\s*\(\s*struct\s+path\s+\*\s*\w+\s*,[^)]+\)',
        r'int ksu_umount_mnt(struct path *path)',
        content
    )
    fixes_applied.append("Fixed ksu_umount_mnt function signature")
    
    # 6. Replace any remaining bare 'flags' variable references with 0
    # But NOT struct member accesses like task->flags or current->flags
    flags_pattern = r'(?<!->)\bflags\b(?!\s*\.)'
    flags_count = len(re.findall(flags_pattern, content))
    if flags_count > 0:
        content = re.sub(flags_pattern, '0', content)
        fixes_applied.append(f"Replaced {flags_count} bare 'flags' references with 0")
    
    # 7. Replace check_mnt with false
    check_mnt_count = len(re.findall(r'\bcheck_mnt\b', content))
    if check_mnt_count:
        content = re.sub(r'\bcheck_mnt\b', 'false', content)
        fixes_applied.append(f"Replaced {check_mnt_count} check_mnt with false")
    
    # 8. Fix KERNEL_VERSION 2-arg calls
    content = re.sub(
        r'KERNEL_VERSION\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)',
        r'KERNEL_VERSION(\1, \2, 0)',
        content
    )
    
    # 9. Fix ksu_task_fix_setuid - remove flags parameter
    content = re.sub(
        r'static\s+int\s+ksu_task_fix_setuid\s*\(([^)]*)\)',
        lambda m: re.sub(r',?\s*int\s+flags\w*', '', m.group(0)),
        content
    )
    
    changes_made = content != original_content
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Fixed {filepath}:")
    if fixes_applied:
        for fix in fixes_applied:
            print(f"  - {fix}")
    else:
        print("  - No changes needed")
    
    # Verify
    remaining_flags = len(re.findall(r'(?<!->)\bflags\b(?!\s*\.)', content))
    remaining_path_umount = len(re.findall(r'path_umount\s*\(', content))
    bad_ksu_calls = len(re.findall(r'ksu_umount_mnt\s*\([^)]+,', content))
    
    if remaining_flags > 0:
        print(f"WARNING: {remaining_flags} bare 'flags' references still present")
    else:
        print("VERIFIED: No bare 'flags' references remaining")
    
    if bad_ksu_calls > 0:
        print(f"WARNING: {bad_ksu_calls} ksu_umount_mnt calls with multiple args still present")
    else:
        print("VERIFIED: All ksu_umount_mnt calls have single argument")
    
    if remaining_path_umount > 0:
        print(f"WARNING: {remaining_path_umount} path_umount calls still present")
    
    return changes_made

def main():
    if len(sys.argv) < 2:
        ksu_dir = os.environ.get('KSU_DIR', '/tmp/ksu_test')
    else:
        ksu_dir = sys.argv[1]
    
    core_hook = os.path.join(ksu_dir, 'core_hook.c')
    
    if not os.path.exists(core_hook):
        print(f"ERROR: {core_hook} not found!")
        sys.exit(1)
    
    fix_core_hook_c(core_hook)
    print("Kernel 4.9 compatibility fixes v21 applied successfully!")

if __name__ == '__main__':
    main()
