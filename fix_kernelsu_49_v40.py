#!/usr/bin/env python3
"""
Kernel 4.9 compatibility fix for KernelSU-Next v1.0.7 - v40
FINAL FIX: Properly handles flags variable declaration and ksu_umount_mnt calls
"""

import sys
import os
import re

def fix_ksu_umount_mnt_calls(content):
    """
    Fix ksu_umount_mnt calls that use undeclared 'flags' variable.
    Replace ksu_umount_mnt(&path, flags) with proper umount call.
    """
    original = content
    changes = []

    # Pattern 1: ksu_umount_mnt(&path, flags) -> sys_umount(path->mnt, flags) if path is struct path
    # Pattern 2: ksu_umount_mnt(&path, flags) -> umount(path) if path is char*

    # First, let's check what type 'path' is in the context
    # For kernel 4.9, we need to use sys_umount or ksys_umount

    # Replace ksu_umount_mnt(&path, flags) with a kernel 4.9 compatible version
    # The flags variable needs to be declared or the call needs to use a literal

    # Pattern: ksu_umount_mnt(&path, flags) where flags is undeclared
    # Replace with: sys_umount(path.mnt, flags) or just umount the path

    # Find all ksu_umount_mnt calls and analyze context
    lines = content.split('\n')
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this line contains ksu_umount_mnt with flags
        if 'ksu_umount_mnt' in line and 'flags' in line:
            # Check if flags is declared in this function
            func_start = i
            while func_start > 0:
                if lines[func_start].strip().startswith('static') or \
                   lines[func_start].strip().startswith('int ') or \
                   lines[func_start].strip().startswith('void '):
                    break
                func_start -= 1

            # Get function context
            func_context = '\n'.join(lines[func_start:i+1])
            flags_declared = 'int flags' in func_context or ', flags)' in func_context

            if not flags_declared:
                # flags is not declared - need to fix this call
                changes.append(f"Line {i+1}: Fixing undeclared 'flags' in ksu_umount_mnt call")

                # Replace ksu_umount_mnt(&path, flags) with ksu_umount_mnt(&path, 0)
                # or with a direct umount call
                new_line = re.sub(
                    r'ksu_umount_mnt\s*\(\s*(&\w+)\s*,\s*flags\s*\)',
                    r'ksu_umount_mnt(\1, 0)',
                    line
                )

                # If still has flags (different pattern), try another replacement
                if 'flags' in new_line:
                    new_line = re.sub(
                        r'ksu_umount_mnt\s*\(\s*([^,]+)\s*,\s*flags\s*\)',
                        r'ksu_umount_mnt(\1, 0)',
                        line
                    )

                if new_line != line:
                    line = new_line
                    changes.append(f"  -> Replaced with: {line.strip()}")

        new_lines.append(line)
        i += 1

    return '\n'.join(new_lines), changes


def fix_try_umount_function(content):
    """
    Fix the try_umount function to be kernel 4.9 compatible.
    Ensures flags parameter is properly declared and used.
    """
    original = content
    changes = []

    # Find the try_umount function and ensure it's properly defined
    # Pattern to match try_umount function
    try_umount_pattern = r'(static\s+int\s+try_umount\s*\([^)]*\)\s*\{)'

    def fix_function(match):
        func_start = match.group(1)
        changes.append("Found try_umount function definition")

        # Check if it already has flags parameter
        if 'int flags' in func_start or 'flags)' in func_start:
            return func_start  # Already has flags parameter

        # Add flags parameter if missing
        if 'const char *path)' in func_start:
            new_start = func_start.replace('const char *path)', 'const char *path, int flags)')
            changes.append("Added flags parameter to try_umount")
            return new_start

        return func_start

    content = re.sub(try_umount_pattern, fix_function, content)

    return content, changes


def fix_flags_variable_usage(content):
    """
    Fix places where 'flags' variable is used but not declared.
    This is the main issue causing the build failure.
    """
    original = content
    changes = []
    lines = content.split('\n')
    new_lines = []

    # Track function scope
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
            # Check if this line uses flags as a variable (not in a comment or string)
            if re.search(r'\bflags\b', line) and not line.strip().startswith('//'):
                # Check if flags is declared locally
                func_context = '\n'.join(lines[function_start_line:i+1])
                flags_declared_locally = 'int flags' in func_context or 'unsigned int flags' in func_context

                if not flags_declared_locally:
                    # Need to fix this line - replace flags with 0 or a declared variable
                    changes.append(f"Line {i+1}: Replacing undeclared 'flags' with 0")
                    # Only replace standalone 'flags' (not part of other words)
                    new_line = re.sub(r'\bflags\b', '0', line)
                    line = new_line

        new_lines.append(line)
        i += 1

    return '\n'.join(new_lines), changes


def add_flags_declaration_to_try_umount(content):
    """
    Add 'int flags = 0;' declaration at the start of try_umount function
    if it uses flags but doesn't declare it.
    """
    lines = content.split('\n')
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        new_lines.append(line)

        # Look for try_umount function definition
        if re.match(r'\s*static\s+int\s+try_umount\s*\(', line):
            # Found the function, now look for the opening brace
            j = i
            found_brace = False
            while j < len(lines) and j < i + 10:
                if '{' in lines[j]:
                    found_brace = True
                    # Check if flags is a parameter
                    func_sig = '\n'.join(lines[i:j+1])
                    has_flags_param = 'int flags' in func_sig or ', flags)' in func_sig

                    if not has_flags_param:
                        # Check if the function uses flags variable
                        func_end = j
                        brace_count = 0
                        for k in range(j, min(len(lines), j + 100)):
                            brace_count += lines[k].count('{')
                            brace_count -= lines[k].count('}')
                            if brace_count == 0 and k > j:
                                func_end = k
                                break

                        func_body = '\n'.join(lines[j:func_end])
                        uses_flags = re.search(r'\bflags\b', func_body) is not None

                        if uses_flags:
                            # Add flags declaration after the opening brace
                            indent = len(lines[j]) - len(lines[j].lstrip())
                            new_lines.append(' ' * (indent + 1) + 'int flags = 0;  /* Added for kernel 4.9 compatibility */')

                    break
                j += 1

        i += 1

    return '\n'.join(new_lines)


def process_core_hook_c(filepath):
    """Special handling for core_hook.c which has the flags issue at line 591"""
    print(f"Processing core_hook.c with special handling: {filepath}")

    with open(filepath, 'r') as f:
        content = f.read()

    original = content
    all_changes = []

    # Apply fixes in order
    content, changes = fix_ksu_umount_mnt_calls(content)
    all_changes.extend(changes)

    content, changes = fix_flags_variable_usage(content)
    all_changes.extend(changes)

    content = add_flags_declaration_to_try_umount(content)

    content, changes = fix_try_umount_function(content)
    all_changes.extend(changes)

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  Fixed {len(all_changes)} issues in core_hook.c")
        for change in all_changes[:10]:  # Show first 10 changes
            print(f"    {change}")
        if len(all_changes) > 10:
            print(f"    ... and {len(all_changes) - 10} more")
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

    # Apply general fixes
    content, new_changes = fix_ksu_umount_mnt_calls(content)
    changes.extend(new_changes)

    content, new_changes = fix_flags_variable_usage(content)
    changes.extend(new_changes)

    content, new_changes = fix_try_umount_function(content)
    changes.extend(new_changes)

    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  Fixed {len(changes)} issues")
        return True
    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: fix_kernelsu_49_v40.py <kernel_directory>")
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
        # Try alternative locations
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
                # Special handling for core_hook.c
                if process_core_hook_c(filepath):
                    files_modified += 1
            else:
                if process_file(filepath):
                    files_modified += 1

    print(f"\nProcessed {files_processed} files, modified {files_modified}")

    # Show line 591 of core_hook.c for verification
    core_hook = os.path.join(ksu_kernel_dir, 'core_hook.c')
    if os.path.exists(core_hook):
        with open(core_hook, 'r') as f:
            lines = f.readlines()
            if len(lines) >= 591:
                print(f"\nVerification - Line 591 of core_hook.c:")
                print(f"  {lines[590].rstrip()}")
                if 'flags' in lines[590] and 'int flags' not in lines[590]:
                    print("  WARNING: Line 591 still contains undeclared 'flags'!")
                else:
                    print("  OK: Line 591 looks good")


if __name__ == '__main__':
    main()
