#!/usr/bin/env python3
"""
Kernel 4.9 compatibility fix for KernelSU-Next v1.0.7 - v41
CRITICAL FIX: Fix syntax error 'current_thread_info()->0' -> 'current_thread_info()->flags'
"""

import sys
import os
import re

def fix_current_thread_info_syntax(content):
    """
    Fix the syntax error where current_thread_info()->0 should be current_thread_info()->flags
    This is a bug in the pre-patched file where '0' is used instead of the struct member name.
    """
    changes = []
    original = content

    # Pattern 1: current_thread_info()->0 -> current_thread_info()->flags
    if 'current_thread_info()->0' in content:
        content = content.replace('current_thread_info()->0', 'current_thread_info()->flags')
        changes.append("Fixed current_thread_info()->0 -> current_thread_info()->flags")

    # Pattern 2: current_thread_info()->1 (if it exists)
    if 'current_thread_info()->1' in content:
        content = content.replace('current_thread_info()->1', 'current_thread_info()->work')
        changes.append("Fixed current_thread_info()->1 -> current_thread_info()->work")

    # Pattern 3: Check for other numeric constants after ->
    # This is a broader fix for any similar issues
    pattern = r'current_thread_info\(\)->(\d+)'
    matches = re.findall(pattern, content)
    for match in set(matches):
        # Map common indices to field names
        if match == '0':
            content = re.sub(rf'current_thread_info\(\)->{match}\b', 'current_thread_info()->flags', content)
        elif match == '1':
            content = re.sub(rf'current_thread_info\(\)->{match}\b', 'current_thread_info()->work', content)
        else:
            # For any other numbers, default to flags
            content = re.sub(rf'current_thread_info\(\)->{match}\b', 'current_thread_info()->flags', content)
        changes.append(f"Fixed current_thread_info()->{match} -> current_thread_info()->flags")

    return content, changes


def fix_ksu_umount_mnt_calls(content):
    """
    Fix ksu_umount_mnt calls that use undeclared 'flags' variable.
    """
    original = content
    changes = []

    # Pattern: ksu_umount_mnt(&path, flags) -> ksu_umount_mnt(&path, 0)
    content = re.sub(
        r'ksu_umount_mnt\s*\(\s*(&\w+)\s*,\s*flags\s*\)',
        r'ksu_umount_mnt(\1, 0)',
        content
    )

    if content != original:
        changes.append("Fixed ksu_umount_mnt calls with undeclared flags")

    return content, changes


def fix_flags_variable_usage(content):
    """
    Fix places where 'flags' variable is used but not declared.
    """
    changes = []
    lines = content.split('\n')
    new_lines = []

    in_function = False
    function_has_flags_param = False
    brace_depth = 0
    function_start_line = 0

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect function start
        func_match = re.match(r'^(static\s+)?(int|void|bool|long)\s+(\w+)\s*\(([^)]*)\)', line)
        if func_match and not in_function:
            in_function = True
            function_has_flags_param = 'flags' in func_match.group(4)
            brace_depth = 0
            function_start_line = i

        # Track braces
        if in_function:
            brace_depth += line.count('{')
            brace_depth -= line.count('}')
            if brace_depth <= 0 and '{' in ''.join(lines[function_start_line:i+1]):
                in_function = False
                function_has_flags_param = False

        # Check for flags variable usage
        if in_function and not function_has_flags_param:
            if re.search(r'\bflags\b', line) and not line.strip().startswith('//'):
                func_context = '\n'.join(lines[function_start_line:i+1])
                flags_declared_locally = 'int flags' in func_context or 'unsigned int flags' in func_context

                if not flags_declared_locally:
                    changes.append(f"Line {i+1}: Replacing undeclared 'flags' with 0")
                    new_line = re.sub(r'\bflags\b', '0', line)
                    line = new_line

        new_lines.append(line)
        i += 1

    return '\n'.join(new_lines), changes


def process_core_hook_c(filepath):
    """Special handling for core_hook.c"""
    print(f"Processing core_hook.c: {filepath}")

    with open(filepath, 'r') as f:
        content = f.read()

    original = content
    all_changes = []

    # Apply fixes in order
    content, changes = fix_current_thread_info_syntax(content)
    all_changes.extend(changes)

    content, changes = fix_ksu_umount_mnt_calls(content)
    all_changes.extend(changes)

    content, changes = fix_flags_variable_usage(content)
    all_changes.extend(changes)

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  Fixed {len(all_changes)} issues in core_hook.c")
        for change in all_changes:
            print(f"    {change}")

        # Show relevant lines for verification
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'disable_seccomp' in line or (130 <= i <= 135 and 'current_thread_info' in line):
                print(f"    Line {i}: {line.strip()}")

        return True
    else:
        print(f"  No changes needed in core_hook.c")
        return False


def process_file(filepath):
    """Process a single source file"""
    filename = os.path.basename(filepath)
    print(f"Processing: {filename}")

    with open(filepath, 'r') as f:
        content = f.read()

    original = content
    changes = []

    content, new_changes = fix_current_thread_info_syntax(content)
    changes.extend(new_changes)

    content, new_changes = fix_ksu_umount_mnt_calls(content)
    changes.extend(new_changes)

    content, new_changes = fix_flags_variable_usage(content)
    changes.extend(new_changes)

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  Fixed {len(changes)} issues")
        return True
    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: fix_kernelsu_49_v41.py <kernel_directory>")
        sys.exit(1)

    kernel_dir = sys.argv[1]
    ksu_kernel_dir = os.path.join(kernel_dir, 'drivers', 'kernelsu')

    # Check if drivers/kernelsu is a symlink
    if os.path.islink(ksu_kernel_dir):
        real_path = os.readlink(ksu_kernel_dir)
        if not os.path.isabs(real_path):
            real_path = os.path.join(os.path.dirname(ksu_kernel_dir), real_path)
        ksu_kernel_dir = os.path.normpath(real_path)
        print(f"Resolved symlink to: {ksu_kernel_dir}")

    if not os.path.exists(ksu_kernel_dir):
        print(f"ERROR: KernelSU kernel directory not found: {ksu_kernel_dir}")
        for alt in ['KernelSU/kernel', 'KernelSU-Next/kernel']:
            alt_path = os.path.join(kernel_dir, alt)
            if os.path.exists(alt_path):
                ksu_kernel_dir = alt_path
                print(f"Using alternative: {ksu_kernel_dir}")
                break
        else:
            print("ERROR: Could not find KernelSU kernel directory")
            sys.exit(1)

    print(f"KernelSU kernel directory: {ksu_kernel_dir}")

    # Process all .c and .h files
    files_processed = 0
    files_modified = 0

    for filename in os.listdir(ksu_kernel_dir):
        if filename.endswith(('.c', '.h')):
            filepath = os.path.join(ksu_kernel_dir, filename)
            files_processed += 1

            if filename == 'core_hook.c':
                if process_core_hook_c(filepath):
                    files_modified += 1
            else:
                if process_file(filepath):
                    files_modified += 1

    print(f"\nProcessed {files_processed} files, modified {files_modified}")

    # Final verification
    core_hook = os.path.join(ksu_kernel_dir, 'core_hook.c')
    if os.path.exists(core_hook):
        with open(core_hook, 'r') as f:
            lines = f.readlines()
            print(f"\nVerification - disable_seccomp function:")
            for i, line in enumerate(lines[125:140], start=126):
                if 'disable_seccomp' in line or 'current_thread_info' in line or 'TIF_SECCOMP' in line:
                    print(f"  Line {i}: {line.rstrip()}")


if __name__ == '__main__':
    main()
