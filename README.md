# Droidspaces Kernel Build

CI/CD pipeline for building crDroid kernel with Droidspaces container support for OnePlus 6/6T.

## Overview

This repository contains GitHub Actions workflows for building Android kernels with Droidspaces (Docker for Android) support on legacy 4.9.x kernels.

### Key Features

- **Automated weekly builds** via GitHub Actions
- **Manual trigger support** for on-demand builds
- **GitHub-hosted ARM64 runners** (pay-as-you-go, ~$1-2 per build)
- **Droidspaces patches** automatically applied from [ravindu644/Droidspaces-OSS](https://github.com/ravindu644/Droidspaces-OSS)

## Supported Devices

| Device | Codename | Kernel | Base ROM |
|--------|----------|--------|----------|
| OnePlus 6 | enchilada | 4.9.x | crDroid 15.0 |
| OnePlus 6T | fajita | 4.9.x | crDroid 15.0 |

## Kernel Configuration

The build applies the following Droidspaces-specific configurations:

```
# Container support
CONFIG_NAMESPACES=y
CONFIG_CGROUP_DEVICE=y
CONFIG_CGROUP_PIDS=y
CONFIG_MEMCG=y
CONFIG_SECCOMP=y

# Networking (NAT mode mandatory for Android)
CONFIG_VETH=y
CONFIG_BRIDGE=y
CONFIG_BRIDGE_NETFILTER=y
CONFIG_NETFILTER_XT_MATCH_ADDRTYPE=y

# Storage
CONFIG_OVERLAY_FS=y
CONFIG_DEVTMPFS=y

# Required: Disable for container internet access
# CONFIG_ANDROID_PARANOID_NETWORK is not set
```

## Build Triggers

- **Weekly**: Sundays at 2 AM UTC
- **Manual**: Via GitHub Actions "Run workflow" button
- **Parameters**:
  - `crdroid_branch`: Target crDroid branch (default: `15.0`)
  - `build_type`: `release` (creates GitHub release) or `debug`

## Build Costs

This workflow uses GitHub-hosted ARM64 runners:
- **Price:** ~$0.016/minute (~$1/hour of build time)
- **Typical kernel build:** 1-2 hours = ~$1-2 per build
- **Weekly automated builds:** ~$4-8/month if running every Sunday

To minimize costs:
- Disable scheduled builds if not actively developing
- Use manual triggers for one-off builds
- Builds only run when you explicitly trigger them

## Installation

1. Download `Image.gz-dtb` and `dtbo.img` from the latest release
2. Flash to your device:
   ```bash
   fastboot flash boot Image.gz-dtb
   fastboot flash dtbo dtbo.img
   ```
3. Install [Droidspaces APK](https://github.com/ravindu644/Droidspaces-OSS/releases)
4. Start a container: `docker run --rm hello-world`

## Troubleshooting

**Issue**: Containers have no internet  
**Fix**: Ensure `CONFIG_ANDROID_PARANOID_NETWORK` is disabled in kernel config

**Issue**: Docker fails with "cgroup mountpoint does not exist"  
**Fix**: Kernel needs `CONFIG_CGROUP_DEVICE=y` and cgroupfs driver (not systemd)

**Issue**: Storage driver errors  
**Fix**: Droidspaces uses `vfs` driver on 4.9 kernels (overlay requires newer kernel)

## CVE Monitoring

This project includes automated CVE monitoring for the 4.9.x kernel. Check the `kernel-cve-watcher` cronjob for security updates.

## Credits

- [ravindu644/Droidspaces-OSS](https://github.com/ravindu644/Droidspaces-OSS) - Droidspaces patches and documentation
- [crDroid](https://github.com/crdroidandroid) - Base ROM and kernel source

## License

Build scripts and workflows: MIT
Kernel and Droidspaces patches: Follow upstream licenses
