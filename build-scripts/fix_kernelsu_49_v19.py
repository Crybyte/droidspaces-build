#!/usr/bin/env python3
"""
CRITICAL FIX v19: Fixed kernel 4.9 compatibility for KernelSU-Next v1.0.7
Properly handles struct member accesses (e.g., ->flags) vs bare flags variables
"""
import os
import sys
import re

def fix_core_hook_c(filepath):
    """Fix core_hook.c for kernel 4.9 compatibility - FIXED regex approach"""
    
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
    
    # 2. Fix try_umount function definition - multi-line support with re.DOTALL
    # Match patterns like: static void try_umount(const char *mnt, bool check_mnt)
    try_umount_patterns = [
        # Single line: static void try_umount(const char *mnt, bool check_mnt)
        (r'static\s+void\s+try_umount\s*\(\s*const\s+char\s*\*\s*\w+\s*,\s*bool\s+\w+\s*\)', 
         r'static void try_umount(const char *mnt)'),
        # Multi-line: static void try_umount(const char *mnt,\n                              bool check_mnt)
        (r'static\s+void\s+try_umount\s*\(\s*const\s+char\s*\*\s*\w+\s*,\s*\n\s*bool\s+\w+\s*\)', 
         r'static void try_umount(const char *mnt)'),
        # With int instead of bool
        (r'static\s+void\s+try_umount\s*\(\s*const\s+char\s*\*\s*\w+\s*,\s*int\s+\w+\s*\)', 
         r'static void try_umount(const char *mnt)'),
    ]
    
    for pattern, replacement in try_umount_patterns:
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            fixes_applied.append("Fixed try_umount function signature")
            break
    
    # 3. Fix try_umount calls - remove second argument
    # Match try_umount(mnt, true), try_umount(mnt, false), try_umount(mnt, 0), etc.
    content = re.sub(
        r'try_umount\s*\(\s*([^,)]+)\s*,\s*[^)]+\)',
        r'try_umount(\1)',
        content
    )
    fixes_applied.append("Fixed try_umount calls")
    
    # 4. Fix ksu_umount_mnt function definition - remove flags parameter
    ksu_umount_patterns = [
        # Single line
        (r'int\s+ksu_umount_mnt\s*\(\s*struct\s+path\s*\*\s*\w+\s*,\s*int\s+\w+\s*\)',
         r'int ksu_umount_mnt(struct path *path)'),
        # Multi-line
        (r'int\s+ksu_umount_mnt\s*\(\s*struct\s+path\s*\*\s*\w+\s*,\s*\n\s*int\s+\w+\s*\)',
         r'int ksu_umount_mnt(struct path *path)'),
    ]
    
    for pattern, replacement in ksu_umount_patterns:
        if re.search(pattern, content, re.DOTALL):
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            fixes_applied.append("Fixed ksu_umount_mnt function signature")
            break
    
    # 5. Fix ksu_umount_mnt calls - remove second argument
    content = re.sub(
        r'ksu_umount_mnt\s*\(\s*([^,)]+)\s*,\s*[^)]+\)',
        r'ksu_umount_mnt(\1)',
        content
    )
    
    # 6. Fix ksu_task_fix_setuid function - remove flags parameter
    task_fix_patterns = [
        # Single line with various param names
        (r'static\s+int\s+ksu_task_fix_setuid\s*\([^)]+int\s+\w*flags\w*[^)]*\)',
         r'static int ksu_task_fix_setuid(struct cred *new, const struct cred *old, int flags)'),
    ]
    
    # Actually, let's be more surgical - just remove the flags param from the signature
    def fix_task_fix_sig(match):
        sig = match.group(0)
        # Remove int flags or similar from the signature
        sig = re.sub(r',\s*int\s+\w*flags\w*', '', sig)
        return sig
    
    task_fix_pattern = r'static\s+int\s+ksu_task_fix_setuid\s*\([^)]+\)'
    content = re.sub(task_fix_pattern, fix_task_fix_sig, content, flags=re.DOTALL)
    
    # 7. CRITICAL FIX: Replace bare 'flags' variables with 0, but NOT struct member accesses
    # Pattern explanation:
    # - (?<![->]) - negative lookbehind: not preceded by -> or -
    # - \bflags\b - word boundary for flags
    # - (?![a-zA-Z0-9_]) - negative lookahead: not followed by word chars
    # This avoids matching: ->flags, .flags, version_flags, etc.
    
    # First, let's find bare 'flags' usage (as a variable name, not struct member)
    # We need to be careful about struct member accesses
    
    # Replace 'flags' when it's a standalone variable (preceded by space/tab/comma/(/[ etc.)
    # But NOT when it's: ->flags, .flags, part of a larger word
    
    def replace_flags_var(match):
        before = match.group(1)
        after = match.group(2)
        # Don't replace if it looks like a struct member access
        return f"{before}0{after}"
    
    # Pattern: captures chars before and after 'flags' to verify it's not struct access
    # Preceded by: start of line, space, tab, comma, (, [, {, ;, !, =, &, |, +, -, *, /, %, <, >
    # Followed by: end of line, space, tab, comma, ), ], }, ;, !, =, &, |, +, -, *, /, %, <, >
    flags_pattern = r'(^|[\s,\(\[\{\;\!\=\&\|\+\-\*\/\%\<\>\,])(?:\bflags\b)([\s\,\)\]\}\;\!\=\&\|\+\-\*\/\%\<\>]|$)'
    
    flags_matches = len(re.findall(r'(?:^|[\s,\(\[\{\;\!\=\&\|\+\-\*\/\%\<\>])(?:\bflags\b)(?:[\s\,\)\]\}\;\!\=\&\|\+\-\*\/\%\<\>]|$)', content))
    if flags_matches:
        content = re.sub(flags_pattern, r'\10\2', content)
        fixes_applied.append(f"Replaced {flags_matches} bare 'flags' variables with 0")
    
    # 8. Replace check_mnt with false (but not in strings/comments ideally)
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
    
    # 10. Additional: Fix any remaining function signatures with flags parameters
    # Generic pattern for functions we might have missed
    func_with_flags_pattern = r'((?:static\s+)?(?:int|void)\s+\w+\s*\([^)]*?)\bint\s+\w*flags\w*\b([^)]*\))'
    
    def remove_flags_param(match):
        prefix = match.group(1)
        suffix = match.group(2)
        # If there's a comma before flags, remove it too
        if prefix.rstrip().endswith(','):
            prefix = prefix.rstrip()[:-1]
        return prefix + suffix
    
    content = re.sub(func_with_flags_pattern, remove_flags_param, content, flags=re.DOTALL)
    
    changes_made = content != original_content
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Fixed {filepath}:")
    if fixes_applied:
        for fix in fixes_applied:
            print(f"  - {fix}")
    else:
        print("  - No changes needed")
    
    # Verify - but be smarter about what we're looking for
    # We want bare 'flags' variables, not struct members
    remaining_bare_flags = len(re.findall(r'(?:^|[\s,\(\[\{\;\!\=\&\|\+\-\*\/\%\<\>])(?:\bflags\b)(?:[\s\,\)\]\}\;\!\=\&\|\+\-\*\/\%\<\>]|$)', content))
    remaining_path_umount = len(re.findall(r'path_umount\s*\(', content))
    
    # Check for struct member accesses (these are OK)
    struct_flags = len(re.findall(r'[\.\->]flags\b', content))
    
    if remaining_bare_flags > 0:
        print(f"WARNING: {remaining_bare_flags} bare 'flags' references still present")
        # Show context
        for i, line in enumerate(content.split('\n'), 1):
            if re.search(r'(?:^|[\s,\(\[\{\;\!\=\&\|\+\-\*\/\%\<\>])(?:\bflags\b)(?:[\s\,\)\]\}\;\!\=\&\|\+\-\*\/\%\<\>]|$)', line):
                print(f"  Line {i}: {line.strip()[:100]}")
    else:
        print("VERIFIED: No bare 'flags' variables remaining")
    
    if struct_flags > 0:
        print(f"OK: {struct_flags} struct member 'flags' references (expected)")
    
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
    print("Kernel 4.9 compatibility fixes v19 applied successfully!")

if __name__ == '__main__':
    main()
