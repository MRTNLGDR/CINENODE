# Installers

This folder receives the signed/unsigned native artifacts created by `scripts/build-tauri.ps1` or `scripts/build-tauri.sh`.

The source package does not contain a prebuilt `Setup.exe`: the current validation environment has no Rust/Tauri toolchain and is not Windows. The build script creates the PyInstaller backend sidecar, validates it, invokes Tauri 2, and copies `.exe`/`.msi`, `.dmg`, `.AppImage`, `.deb`, or `.rpm` outputs here on the matching operating system.
