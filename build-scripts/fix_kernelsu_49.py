#!/usr/bin/env python3
"""
Fix KernelSU-Next v1.0.7 for kernel 4.9 compatibility.

This script patches the try_umount function definition which uses kernel 5.x
symbols (check_mnt, flags) that don't exist in kernel 4.9.
"""

import re
import sys
import os

def patch_core_hook(filepath):
    """Patch core_hook.c to replace try_umount with kernel 4.9 compatible version."""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Pattern to match the try_umount function
    # Look for the function declaration and its body
    # The function may span multiple lines and contain nested braces
    
    # First, let's find where try_umount is defined
    func_start = content.find('static int try_umount')
    if func_start == -1:
        print(f"try_umount function not found in {filepath}")
        return True
    
    print(f"Found try_umount function at position {func_start}")
    
    # Find the opening brace of the function
    brace_start = content.find('{', func_start)
    if brace_start == -1:
        print("ERROR: Could not find opening brace of try_umount function")
        return False
    
    # Find the matching closing brace
    brace_count = 1
    pos = brace_start + 1
    while brace_count > 0 and pos < len(content):
        if content[pos] == '{':
            brace_count += 1
        elif content[pos] == '}':
            brace_count -= 1
        pos += 1
    
    func_end = pos
    
    # Extract the old function
    old_func = content[func_start:func_end]
    print("Old function found:")
    print("-" * 40)
    print(old_func[:500])
    print("-" * 40)
    
    # New implementation for kernel 4.9
    new_func = '''static int try_umount(const char *mnt, int flags)
{
	struct path path;
	int err = kern_path(mnt, LOOKUP_FOLLOW, &path);
	if (err)
		return err;

	// Kernel 4.9 compatibility: use simple umount instead of path_umount
	// which requires check_mnt() and other 5.x symbols
	err = umount(mnt);

	path_put(&path);
	return err;
}'''
    
    # Replace the function
    content = content[:func_start] + new_func + content[func_end:]
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print("SUCCESS: try_umount function replaced with kernel 4.9 compatible version")
    return True

def patch_path_umount_calls(filepath):
    """Replace any remaining path_umount calls with umount."""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    
    # Replace path_umount(path, flags) with umount(path)
    content = re.sub(r'path_umount\s*\(\s*([^,]+)\s*,[^)]+\)', r'umount(\1)', content)
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Patched path_umount calls in {filepath}")
    
    return True

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <ksu_kernel_dir>")
        sys.exit(1)
    
    ksu_dir = sys.argv[1]
    
    if not os.path.isdir(ksu_dir):
        print(f"ERROR: Directory not found: {ksu_dir}")
        sys.exit(1)
    
    print(f"=== Fixing KernelSU-Next for kernel 4.9 compatibility ===")
    print(f"Target directory: {ksu_dir}")
    
    # Patch core_hook.c
    core_hook = os.path.join(ksu_dir, 'core_hook.c')
    if os.path.exists(core_hook):
        print(f"\nPatching {core_hook}...")
        if not patch_core_hook(core_hook):
            sys.exit(1)
    
    # Patch all .c and .h files for path_umount
    print("\nPatching remaining path_umount calls...")
    for filename in os.listdir(ksu_dir):
        if filename.endswith(('.c', '.h')):
            filepath = os.path.join(ksu_dir, filename)
            patch_path_umount_calls(filepath)
    
    # Verify no path_umount remains
    print("\nVerifying patches...")
    remaining = 0
    for filename in os.listdir(ksu_dir):
        if filename.endswith(('.c', '.h')):
            filepath = os.path.join(ksu_dir, filename)
            with open(filepath, 'r') as f:
                content = f.read()
            if 'path_umount' in content:
                print(f"WARNING: path_umount still found in {filename}")
                remaining += 1
    
    if remaining == 0:
        print("SUCCESS: All path_umount references patched")
    else:
        print(f"WARNING: {remaining} files still contain path_umount references")
    
    print("\n=== KernelSU-Next kernel 4.9 compatibility patching complete ===")

if __name__ == '__main__':
    main()
