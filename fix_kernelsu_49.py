#!/usr/bin/env python3
"""
Kernel 4.9 compatibility fix for KernelSU-Next v1.0.7
Completely rewrites try_umount function definition to avoid check_mnt and flags issues
"""

import sys
import os
import re

def fix_try_umount_definition(content):
    """
    Replace the try_umount function definition with a kernel 4.9 compatible version.
    The issue is that check_mnt() doesn't exist in kernel 4.9 and flags handling is different.
    """
    # Pattern to match the entire try_umount function
    # This is a complex multi-line pattern
    patterns = [
        # Pattern 1: Full function with check_mnt
        r'static\s+int\s+try_umount\s*\([^)]*\)\s*\{[^}]*check_mnt[^}]*\}',
        # Pattern 2: Function with flags parameter
        r'static\s+int\s+try_umount\s*\(\s*const\s+char\s*\*\s*\w+\s*,\s*int\s+\w+\s*\)\s*\{[^}]*\}',
        # Pattern 3: More general function pattern
        r'static\s+int\s+try_umount\s*\([^)]*\)\s*\{[\s\S]*?(?=\nstatic|\n\w+\s+\w+\s*\(|\Z)',
    ]

    # Kernel 4.9 compatible replacement
    replacement = '''static int try_umount(const char *path, int flags)
{
	// Kernel 4.9 compatible version - simplified umount
	// Original used check_mnt() which doesn't exist in 4.9
	int err = 0;

	// Try umount directly (kernel 4.9 compatible)
	// The path lookup and mount checking is handled internally by sys_umount
	err = umount(path);

	// Suppress unused parameter warning
	(void)flags;

	return err;
}'''

    fixed_content = content
    found = False

    # Try each pattern
    for pattern in patterns:
        if re.search(pattern, fixed_content):
            fixed_content = re.sub(pattern, replacement, fixed_content)
            found = True
            print("  Replaced try_umount function definition")
            break

    # If no pattern matched, try to find and comment out problematic lines
    if not found:
        # Look for check_mnt usage and remove/comment it
        lines = fixed_content.split('\n')
        new_lines = []
        in_try_umount = False
        brace_count = 0
        i = 0

        while i < len(lines):
            line = lines[i]

            # Detect start of try_umount function
            if re.match(r'\s*static\s+int\s+try_umount', line):
                in_try_umount = True
                brace_count = 0
                # Replace with compatible version
                new_lines.append('static int try_umount(const char *path, int flags)')
                new_lines.append('{')
                new_lines.append('\t// Kernel 4.9 compatible version')
                new_lines.append('\t(void)flags;  // Suppress unused parameter warning')
                new_lines.append('\treturn umount(path);')
                new_lines.append('}')

                # Skip until we find the end of the original function
                i += 1
                while i < len(lines):
                    if '{' in lines[i]:
                        brace_count += lines[i].count('{')
                    if '}' in lines[i]:
                        brace_count -= lines[i].count('}')
                    i += 1
                    if brace_count <= 0 and '}' in lines[i-1]:
                        break
                in_try_umount = False
                found = True
                continue

            new_lines.append(line)
            i += 1

        if found:
            fixed_content = '\n'.join(new_lines)
            print("  Rewrote try_umount function (pattern fallback)")

    return fixed_content, found


def fix_path_umount_calls(content):
    """Replace path_umount calls with umount"""
    # path_umount(path, flags) -> umount(path)
    content = re.sub(
        r'path_umount\s*\(\s*([^,]+)\s*,\s*[^)]+\)',
        r'umount(\1)',
        content
    )
    return content


def fix_kernel_version_calls(content):
    """Fix KERNEL_VERSION macro calls with 2 arguments"""
    # KERNEL_VERSION(x, y) -> KERNEL_VERSION(x, y, 0)
    content = re.sub(
        r'KERNEL_VERSION\s*\(\s*([0-9]+)\s*,\s*([0-9]+)\s*\)',
        r'KERNEL_VERSION(\1, \2, 0)',
        content
    )
    return content


def fix_try_umount_calls(content):
    """Fix try_umount calls with 2 arguments - keep them as they work with our new signature"""
    # The new signature accepts (path, flags) so calls don't need changing
    # But we need to make sure flags variable exists where used
    return content


def process_file(filepath):
    """Process a single source file"""
    print(f"Processing: {filepath}")

    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content

    # Apply fixes
    content = fix_path_umount_calls(content)
    content = fix_kernel_version_calls(content)
    content, fixed_func = fix_try_umount_definition(content)

    # Check if anything changed
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  Fixed: {filepath}")
        return True
    else:
        print(f"  No changes needed: {filepath}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: fix_kernelsu_49.py <kernelsu_kernel_directory>")
        sys.exit(1)

    ksu_dir = sys.argv[1]

    if not os.path.isdir(ksu_dir):
        print(f"Error: Directory not found: {ksu_dir}")
        sys.exit(1)

    print(f"=== Kernel 4.9 Compatibility Fix for KernelSU-Next ===")
    print(f"Directory: {ksu_dir}")
    print()

    fixed_count = 0

    # Process all .c and .h files
    for filename in os.listdir(ksu_dir):
        if filename.endswith(('.c', '.h')):
            filepath = os.path.join(ksu_dir, filename)
            if process_file(filepath):
                fixed_count += 1

    print()
    print(f"=== Fixed {fixed_count} files ===")

    # Also try to find and patch core_hook.c specifically
    core_hook = os.path.join(ksu_dir, 'core_hook.c')
    if os.path.exists(core_hook):
        print(f"\nSpecial handling for core_hook.c (common location of try_umount)...")
        with open(core_hook, 'r') as f:
            content = f.read()

        # Aggressive fix for try_umount in core_hook.c
        if 'try_umount' in content:
            # Replace the entire try_umount function with a minimal implementation
            # This handles the case where regex fails due to complex function body

            # Find function boundaries more aggressively
            lines = content.split('\n')
            new_lines = []
            i = 0
            replaced = False

            while i < len(lines):
                line = lines[i]

                # Look for try_umount function start
                if re.match(r'^(static\s+)?\s*int\s+try_umount', line) or \
                   ('try_umount' in line and '(' in line and 'static' in line):
                    print(f"  Found try_umount at line {i+1}")

                    # Insert replacement
                    new_lines.append('static int try_umount(const char *path, int flags)')
                    new_lines.append('{')
                    new_lines.append('\t// Kernel 4.9 compatible - simplified implementation')
                    new_lines.append('\t// Original used check_mnt() which is not in kernel 4.9')
                    new_lines.append('\t(void)flags;  // Suppress unused parameter warning')
                    new_lines.append('\treturn umount(path);')
                    new_lines.append('}')

                    # Skip original function body
                    i += 1
                    brace_depth = 0
                    started = False
                    while i < len(lines):
                        if '{' in lines[i]:
                            brace_depth += lines[i].count('{')
                            started = True
                        if '}' in lines[i]:
                            brace_depth -= lines[i].count('}')
                        i += 1
                        if started and brace_depth <= 0:
                            break

                    replaced = True
                    continue

                new_lines.append(line)
                i += 1

            if replaced:
                with open(core_hook, 'w') as f:
                    f.write('\n'.join(new_lines))
                print("  Successfully replaced try_umount in core_hook.c")


if __name__ == '__main__':
    main()
