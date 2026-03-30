#!/usr/bin/env python3
"""
KernelSU-Next v1.0.7 kernel 4.9 compatibility fixer v25
Addresses: 'flags' undeclared in try_umount function at line 591

The actual v1.0.7 code structure:
- Line 563: static int ksu_umount_mnt(struct path *path, int flags)
- Line 566: return path_umount(path, flags);
- Line 573: static void try_umount(const char *mnt, bool check_mnt, int flags)
- Line 591: err = ksu_umount_mnt(&path, flags);  <-- ERROR: flags undeclared in try_umount

This fixer completely rewrites the problematic functions for kernel 4.9 compatibility.
"""

import sys
import re
import os

def fix_core_hook(filepath):
    """Fix core_hook.c for kernel 4.9 compatibility"""

    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}")
        return False

    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content
    fixes_applied = []

    # Fix 1: Replace ksu_umount_mnt function definition and body
    # From v1.0.7:
    # static int ksu_umount_mnt(struct path *path, int flags)
    # {
    # #if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 9, 0) || defined(KSU_UMOUNT)
    #     return path_umount(path, flags);
    # #else
    #     // TODO: umount for non GKI kernel
    #     return -ENOSYS;
    # #endif
    # }
    #
    # To kernel 4.9 compatible:
    # static int ksu_umount_mnt(struct path *path)
    # {
    #     char *buf = kmalloc(PATH_MAX, GFP_KERNEL);
    #     if (!buf)
    #         return -ENOMEM;
    #     char *path_str = dentry_path_raw(path->dentry, buf, PATH_MAX);
    #     int err = umount(path_str);
    #     kfree(buf);
    #     return err;
    # }

    ksu_umount_pattern = r'static int ksu_umount_mnt\(struct path \*path, int flags\)\s*\{[^}]*#if[^#]*#else[^#]*#endif[^}]*\}'
    ksu_umount_replacement = '''static int ksu_umount_mnt(struct path *path)
{
	char *buf = kmalloc(PATH_MAX, GFP_KERNEL);
	if (!buf)
		return -ENOMEM;
	char *path_str = dentry_path_raw(path->dentry, buf, PATH_MAX);
	int err = umount(path_str);
	kfree(buf);
	return err;
}'''

    new_content, count1 = re.subn(ksu_umount_pattern, ksu_umount_replacement, content, flags=re.DOTALL)
    if count1 > 0:
        fixes_applied.append(f"Fixed ksu_umount_mnt function definition and body ({count1} matches)")
        content = new_content
    else:
        # Try simpler pattern - just the function signature
        pattern1b = r'static int ksu_umount_mnt\s*\(\s*struct path\s*\*\s*path\s*,\s*int\s+flags\s*\)'
        replacement1b = 'static int ksu_umount_mnt(struct path *path)'
        new_content, count1b = re.subn(pattern1b, replacement1b, content)
        if count1b > 0:
            fixes_applied.append(f"Fixed ksu_umount_mnt function signature ({count1b} matches)")
            content = new_content

    # Fix 2: Replace try_umount function signature
    # From: static void try_umount(const char *mnt, bool check_mnt, int flags)
    # To: static void try_umount(const char *mnt, bool check_mnt)
    pattern2 = r'static void try_umount\s*\(\s*const char\s*\*\s*mnt\s*,\s*bool\s+check_mnt\s*,\s*int\s+flags\s*\)'
    replacement2 = 'static void try_umount(const char *mnt, bool check_mnt)'
    new_content, count2 = re.subn(pattern2, replacement2, content)
    if count2 > 0:
        fixes_applied.append(f"Fixed try_umount function signature ({count2} matches)")
        content = new_content

    # Fix 3: Replace ksu_umount_mnt(&path, flags) calls with ksu_umount_mnt(&path)
    # This handles line 591 and any other similar calls
    pattern3 = r'ksu_umount_mnt\s*\(\s*&path\s*,\s*flags\s*\)'
    replacement3 = 'ksu_umount_mnt(&path)'
    new_content, count3 = re.subn(pattern3, replacement3, content)
    if count3 > 0:
        fixes_applied.append(f"Fixed {count3} ksu_umount_mnt(&path, flags) calls")
        content = new_content

    # Fix 4: Replace any other ksu_umount_mnt(path, flags) calls
    # Pattern: ksu_umount_mnt(anything, flags) -> ksu_umount_mnt(anything)
    pattern4 = r'ksu_umount_mnt\s*\(\s*([^,]+)\s*,\s*flags\s*\)'
    replacement4 = r'ksu_umount_mnt(\1)'
    new_content, count4 = re.subn(pattern4, replacement4, content)
    if count4 > 0:
        fixes_applied.append(f"Fixed {count4} other ksu_umount_mnt(..., flags) calls")
        content = new_content

    # Fix 5: Handle path_umount calls - replace with umount
    pattern5 = r'path_umount\s*\(\s*path\s*,\s*flags\s*\)'
    replacement5 = 'umount(path)'
    new_content, count5 = re.subn(pattern5, replacement5, content)
    if count5 > 0:
        fixes_applied.append(f"Fixed {count5} path_umount calls")
        content = new_content

    # Fix 6: Replace bare 'flags' variable references (but not in struct accesses like ->flags)
    # This is tricky - we need to replace 'flags' when it's a variable but not when it's part of a struct member
    # Pattern: match 'flags' when it's surrounded by non-identifier characters
    pattern6 = r'(?<![a-zA-Z0-9_])flags(?![a-zA-Z0-9_])'
    # But we need to be careful - if there are still flags parameters, this could break things
    # Let's only do this inside try_umount function body

    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✓ Fixed {filepath}")
        for fix in fixes_applied:
            print(f"  - {fix}")
        return True
    else:
        print(f"No changes needed for {filepath}")
        # Let's verify what we found
        if 'ksu_umount_mnt(struct path *path, int flags)' in content:
            print("  WARNING: Found 'ksu_umount_mnt(struct path *path, int flags)' but couldn't fix it")
        if 'try_umount(const char *mnt, bool check_mnt, int flags)' in content:
            print("  WARNING: Found 'try_umount(const char *mnt, bool check_mnt, int flags)' but couldn't fix it")
        if 'ksu_umount_mnt(&path, flags)' in content:
            print("  WARNING: Found 'ksu_umount_mnt(&path, flags)' but couldn't fix it")
        return False


def main():
    if len(sys.argv) > 1:
        ksu_dir = sys.argv[1]
    else:
        ksu_dir = os.environ.get('KSU_DIR', 'KernelSU/kernel')

    core_hook = os.path.join(ksu_dir, 'core_hook.c')

    print(f"=== KernelSU-Next v1.0.7 kernel 4.9 compatibility fixer v25 ===")
    print(f"Target: {core_hook}")
    print()

    success = fix_core_hook(core_hook)

    if success:
        print("\n✓ Fixes applied successfully")
        sys.exit(0)
    else:
        print("\n✗ No fixes applied")
        sys.exit(1)


if __name__ == '__main__':
    main()
