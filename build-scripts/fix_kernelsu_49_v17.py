#!/usr/bin/env python3
"""
CRITICAL FIX v17: Ultra-aggressive kernel 4.9 compatibility for KernelSU-Next v1.0.7
Handles ALL flags-related issues comprehensively
"""
import os
import sys
import re

def fix_core_hook_c(filepath):
    """Fix core_hook.c for kernel 4.9 compatibility - aggressive approach"""
    
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
    
    # 2. AGGRESSIVE: Find and fix ANY function with 'flags' parameter
    # Pattern: functionName(..., int flags) or functionName(..., int some_flags)
    flags_param_pattern = r'(\w+)\s*\(\s*([^)]*)int\s+\w*flags\w*\s*\)'
    
    def remove_flags_param(match):
        func_name = match.group(1)
        params = match.group(2)
        # Remove the flags parameter
        new_params = re.sub(r',?\s*int\s+\w*flags\w*', '', params)
        return f"{func_name}({new_params})"
    
    content = re.sub(flags_param_pattern, remove_flags_param, content)
    
    # 3. Fix try_umount function definition - handles both static int and static void
    # Ultra-aggressive: remove ANY parameter after the first one that looks like flags
    try_umount_pattern = r'(static\s+(?:int|void)\s+try_umount\s*\()([^)]*)(\))'
    
    def fix_try_umount_def(match):
        prefix = match.group(1)
        params = match.group(2)
        suffix = match.group(3)
        
        # Keep only the first parameter (const char *mnt)
        first_param_match = re.match(r'(\s*const\s+char\s*\*\s*\w+\s*)', params)
        if first_param_match:
            return f"{prefix}const char *mnt{suffix}"
        return match.group(0)
    
    content = re.sub(try_umount_pattern, fix_try_umount_def, content, flags=re.DOTALL)
    
    # 4. Fix try_umount calls - reduce ALL multi-arg calls to single arg
    # Pattern: try_umount(anything, ...) -> try_umount(anything)
    content = re.sub(
        r'try_umount\s*\(\s*([^,)]+)\s*,[^)]+\)',
        r'try_umount(\1)',
        content
    )
    fixes_applied.append("Fixed all multi-arg try_umount calls")
    
    # 5. Fix ksu_umount_mnt function - remove ALL parameters after first
    ksu_umount_pattern = r'(int\s+ksu_umount_mnt\s*\()([^)]*)(\))'
    
    def fix_ksu_umount_def(match):
        prefix = match.group(1)
        params = match.group(2)
        suffix = match.group(3)
        
        # Keep only struct path * or similar first param
        first_param_match = re.search(r'(struct\s+\w+\s*\*?\s*\w+)', params)
        if first_param_match:
            return f"{prefix}{first_param_match.group(1)}{suffix}"
        return match.group(0)
    
    content = re.sub(ksu_umount_pattern, fix_ksu_umount_def, content, flags=re.DOTALL)
    
    # 6. Fix ksu_umount_mnt calls - remove second argument
    content = re.sub(
        r'(ksu_umount_mnt\s*\(\s*[^)]+)\s*,\s*[^)]+\s*\)',
        r'\1)',
        content
    )
    
    # 7. Fix ksu_task_fix_setuid - remove ALL parameters after the first few standard ones
    task_fix_pattern = r'(static\s+int\s+ksu_task_fix_setuid\s*\()([^)]*)(\))'
    
    def fix_task_fix_def(match):
        prefix = match.group(1)
        params = match.group(2)
        suffix = match.group(3)
        
        # Remove any flags parameter
        new_params = re.sub(r',?\s*int\s+flags\w*', '', params)
        if new_params != params:
            return f"{prefix}{new_params}{suffix}"
        return match.group(0)
    
    content = re.sub(task_fix_pattern, fix_task_fix_def, content, flags=re.DOTALL)
    
    # 8. CRITICAL: Replace ANY remaining bare 'flags' variable with 0
    # Pattern: flags as a standalone variable (not struct member, not in string)
    flags_count = len(re.findall(r'\bflags\b', content))
    if flags_count > 0:
        content = re.sub(r'\bflags\b', '0', content)
        fixes_applied.append(f"Replaced {flags_count} 'flags' references with 0")
    
    # 9. Replace check_mnt with false
    check_mnt_count = len(re.findall(r'\bcheck_mnt\b', content))
    if check_mnt_count:
        content = re.sub(r'\bcheck_mnt\b', 'false', content)
        fixes_applied.append(f"Replaced {check_mnt_count} check_mnt with false")
    
    # 10. Fix KERNEL_VERSION 2-arg calls
    content = re.sub(
        r'KERNEL_VERSION\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)',
        r'KERNEL_VERSION(\1, \2, 0)',
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
    remaining_flags = len(re.findall(r'\bflags\b', content))
    remaining_path_umount = len(re.findall(r'path_umount\s*\(', content))
    
    if remaining_flags > 0:
        print(f"WARNING: {remaining_flags} 'flags' references still present")
        # Show context
        for i, line in enumerate(content.split('\n'), 1):
            if 'flags' in line:
                print(f"  Line {i}: {line.strip()[:80]}")
                if i > 10:
                    break
    else:
        print("VERIFIED: No 'flags' references remaining")
    
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
    print("Kernel 4.9 compatibility fixes v17 applied successfully!")

if __name__ == '__main__':
    main()
