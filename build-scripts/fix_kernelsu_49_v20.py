#!/usr/bin/env python3
"""
CRITICAL FIX v20: Ultra-aggressive kernel 4.9 compatibility for KernelSU-Next v1.0.7
Addresses remaining flags issues that v19 missed - more comprehensive patterns
"""
import os
import sys
import re

def fix_core_hook_c(filepath):
    """Fix core_hook.c for kernel 4.9 compatibility - ULTRA AGGRESSIVE approach"""
    
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
    
    # 2. AGGRESSIVE FIX for ksu_umount_mnt calls - remove ALL second arguments
    # Pattern explanation:
    # - ksu_umount_mnt\s*\( - match function call start
    # - \s* - optional whitespace
    # - (&?\w+) - capture first argument (could be &path, path, mnt, etc.)
    # - \s*,\s* - comma with optional whitespace
    # - [^)]+ - anything until closing paren (the second argument)
    # - \) - closing paren
    ksu_umount_count = len(re.findall(r'ksu_umount_mnt\s*\(', content))
    if ksu_umount_count:
        # Strategy 1: Handle calls with & prefix (like &path)
        content = re.sub(
            r'ksu_umount_mnt\s*\(\s*(&[\w.]+)\s*,[^)]+\)',
            r'ksu_umount_mnt(\1)',
            content
        )
        # Strategy 2: Handle calls without & prefix
        content = re.sub(
            r'ksu_umount_mnt\s*\(\s*([\w.]+)\s*,[^)]+\)',
            r'ksu_umount_mnt(\1)',
            content
        )
        fixes_applied.append(f"Fixed {ksu_umount_count} ksu_umount_mnt calls")
    
    # 3. Fix try_umount calls - ULTRA AGGRESSIVE
    try_umount_count = len(re.findall(r'try_umount\s*\(', content))
    if try_umount_count:
        # Remove all arguments after the first
        content = re.sub(
            r'try_umount\s*\(\s*([^,)]+)[^)]*\)',
            r'try_umount(\1)',
            content
        )
        fixes_applied.append(f"Fixed {try_umount_count} try_umount calls")
    
    # 4. Fix try_umount function definition - remove ALL extra parameters
    try_umount_def = re.search(r'static\s+void\s+try_umount\s*\([^)]+\)', content, re.DOTALL)
    if try_umount_def:
        # Replace with single parameter version
        content = re.sub(
            r'static\s+void\s+try_umount\s*\([^)]+\)',
            r'static void try_umount(const char *mnt)',
            content,
            flags=re.DOTALL
        )
        fixes_applied.append("Fixed try_umount function signature")
    
    # 5. Fix ksu_umount_mnt function definition - remove flags parameter
    ksu_umount_def = re.search(r'int\s+ksu_umount_mnt\s*\([^)]+\)', content, re.DOTALL)
    if ksu_umount_def:
        content = re.sub(
            r'int\s+ksu_umount_mnt\s*\([^)]+\)',
            r'int ksu_umount_mnt(struct path *path)',
            content,
            flags=re.DOTALL
        )
        fixes_applied.append("Fixed ksu_umount_mnt function signature")
    
    # 6. Fix ksu_task_fix_setuid function - remove flags parameter
    content = re.sub(
        r'static\s+int\s+ksu_task_fix_setuid\s*\(\s*struct\s+cred\s*\*\s*new\s*,\s*const\s+struct\s+cred\s*\*\s*old[^)]*\)',
        r'static int ksu_task_fix_setuid(struct cred *new, const struct cred *old)',
        content,
        flags=re.DOTALL
    )
    
    # 7. ULTRA-AGGRESSIVE: Replace ANY remaining bare 'flags' with 0
    # Use word boundary and context check to avoid struct member accesses
    # This is more aggressive than v19
    flags_count = 0
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        original_line = line
        # Replace bare 'flags' (not preceded by -> or . or word char)
        # and not followed by word char
        new_line = re.sub(r'(?<![\w\-\.>])\bflags\b(?![\w])', '0', line)
        if new_line != original_line:
            flags_count += 1
        new_lines.append(new_line)
    content = '\n'.join(new_lines)
    if flags_count:
        fixes_applied.append(f"Replaced {flags_count} bare 'flags' variables with 0")
    
    # 8. Replace check_mnt with false
    check_mnt_count = len(re.findall(r'\bcheck_mnt\b', content))
    if check_mnt_count:
        content = re.sub(r'\bcheck_mnt\b', 'false', content)
        fixes_applied.append(f"Replaced {check_mnt_count} check_mnt with false")
    
    # 9. Fix KERNEL_VERSION 2-arg calls
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
    
    # Verification
    remaining_flags = len(re.findall(r'(?<![\w\-\.>])\bflags\b(?![\w])', content))
    remaining_path_umount = len(re.findall(r'path_umount\s*\(', content))
    
    if remaining_flags > 0:
        print(f"WARNING: {remaining_flags} bare 'flags' references still present")
        for i, line in enumerate(content.split('\n'), 1):
            if re.search(r'(?<![\w\-\.>])\bflags\b(?![\w])', line):
                print(f"  Line {i}: {line.strip()[:100]}")
    else:
        print("VERIFIED: No bare 'flags' variables remaining")
    
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
    print("Kernel 4.9 compatibility fixes v20 applied successfully!")

if __name__ == '__main__':
    main()
