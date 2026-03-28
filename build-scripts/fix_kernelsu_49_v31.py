#!/usr/bin/env python3
"""
KernelSU-Next v1.0.7 Kernel 4.9 Compatibility Fix v31
COMPREHENSIVE: Multi-location patching with verification

This fix ensures the pre-patched core_hook.c is applied to ALL possible
locations the compiler might use, handling symlink issues.
"""

import sys
import os
import shutil

def find_core_hook_files(base_dir):
    """Find all possible core_hook.c locations"""
    candidates = []
    
    # Check all possible paths
    paths_to_check = [
        "drivers/kernelsu/core_hook.c",
        "KernelSU/kernel/core_hook.c",
        "KernelSU-Next/kernel/core_hook.c",
    ]
    
    # Also check where drivers/kernelsu symlink points to
    kernelsu_link = os.path.join(base_dir, "drivers/kernelsu")
    if os.path.islink(kernelsu_link):
        real_path = os.path.realpath(kernelsu_link)
        if real_path != kernelsu_link:
            candidates.append(os.path.join(real_path, "core_hook.c"))
    
    for path in paths_to_check:
        full_path = os.path.join(base_dir, path)
        if os.path.exists(full_path):
            # Get the real path (resolve symlinks)
            real_path = os.path.realpath(full_path)
            if real_path not in candidates:
                candidates.append(real_path)
            # Also add the original path
            if full_path not in candidates and full_path != real_path:
                candidates.append(full_path)
    
    return candidates

def apply_prepatched_file(prepatched_path, target_path):
    """Apply the pre-patched file"""
    try:
        # Backup original
        backup_path = target_path + '.v31.bak'
        if os.path.exists(target_path):
            shutil.copy2(target_path, backup_path)
        
        # Copy pre-patched file
        shutil.copy2(prepatched_path, target_path)
        
        # Verify line 591
        with open(target_path) as f:
            lines = f.readlines()
            if len(lines) < 591:
                print(f"  ERROR: File has only {len(lines)} lines; expected at least 591")
                return False
            line_591 = lines[590].strip()
            if 'flags' in line_591 and 'ksu_umount_mnt' in line_591:
                print(f"  ERROR: Line 591 still has 'flags' after copy in {target_path}!")
                return False
        
        return True
    except Exception as e:
        print(f"  ERROR applying to {target_path}: {e}")
        return False

def verify_line_591(filepath):
    """Verify line 591 is fixed"""
    try:
        with open(filepath) as f:
            lines = f.readlines()
            if len(lines) < 591:
                return False, f"File has only {len(lines)} lines; missing line 591"
            line_591 = lines[590].rstrip()
            print(f"  Line 591: {line_591[:80]}")
            if 'flags' in line_591 and 'ksu_umount_mnt' in line_591:
                return False, "Line 591 still contains 'flags' variable"
        return True, "Line 591 looks correct"
    except Exception as e:
        return False, f"Error reading file: {e}"

def main():
    kernel_dir = os.environ.get('KERNEL_DIR', '')
    if not kernel_dir and len(sys.argv) > 1:
        kernel_dir = sys.argv[1]
    
    if not kernel_dir:
        print("Error: Kernel directory not specified")
        print("Usage: KERNEL_DIR=/path/to/kernel python3 fix_kernelsu_49_v31.py")
        sys.exit(1)
    
    # Path to pre-patched file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prepatched_path = os.path.join(script_dir, 'core_hook.c.patched')
    
    if not os.path.exists(prepatched_path):
        print(f"ERROR: Pre-patched file not found: {prepatched_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("KernelSU-Next v1.0.7 Kernel 4.9 Compatibility Fix v31")
    print("COMPREHENSIVE Multi-Location Patching")
    print("=" * 60)
    
    # Find all core_hook.c locations
    core_hook_files = find_core_hook_files(kernel_dir)
    
    print(f"\nKernel directory: {kernel_dir}")
    print(f"Pre-patched file: {prepatched_path}")
    print(f"\nFound {len(core_hook_files)} core_hook.c location(s):")
    for f in core_hook_files:
        print(f"  - {f}")
    
    # Apply to all locations
    success_count = 0
    print("\n" + "=" * 60)
    print("Applying pre-patched file to all locations...")
    print("=" * 60)
    
    for target_path in core_hook_files:
        print(f"\nPatching: {target_path}")
        if apply_prepatched_file(prepatched_path, target_path):
            success_count += 1
            print("  SUCCESS: Applied pre-patched file")
            # Verify
            ok, msg = verify_line_591(target_path)
            print(f"  Verification: {msg}")
    
    print("\n" + "=" * 60)
    print(f"Results: {success_count}/{len(core_hook_files)} files patched")
    print("=" * 60)
    
    if success_count == 0:
        print("ERROR: Failed to patch any files!")
        sys.exit(1)
    
    # Final verification
    print("\nFinal verification of all patched files:")
    all_good = True
    for target_path in core_hook_files:
        ok, msg = verify_line_591(target_path)
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {os.path.basename(os.path.dirname(target_path))}/core_hook.c: {msg}")
        if not ok:
            all_good = False
    
    if all_good:
        print("\n✓ SUCCESS: All files patched and verified!")
        sys.exit(0)
    else:
        print("\n✗ FAILURE: Some files still have issues!")
        sys.exit(1)

if __name__ == '__main__':
    main()
