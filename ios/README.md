# VT3 on iOS (experimental)

This folder documents the new iOS build path. The iOS target uses the existing C runtime, statically
recompiled code generated from the owner's `VT3.exe`, SDL3 for UIKit/input/audio, and Vulkan through
MoltenVK. There is no retail game code or data committed here.

## Build from GitHub Actions

1. Push this repository to your own GitHub repository.
2. In **Settings → Secrets and variables → Actions**, add `VT3_EXE_URL` with a direct HTTPS URL
   for your own supported English v1.0.1 `VT3.exe`, or a ZIP containing it. The current workflow
   also accepts optional `VT3_EXE_AUTH_HEADER` if the host needs an HTTP authorization header.
3. Open **Actions → Build VT3 iOS IPA → Run workflow**.
4. When the job completes, download the `VT3-iOS-unsigned-IPA` artifact. It is an unsigned IPA and
   must be re-signed with your Apple ID before it can be installed on an iPhone.

The build validates the executable in `build.py`. A different executable revision is rejected.
The hosted runner downloads SDL3 and builds SDL3/MoltenVK from their upstream repositories, then
translates the supplied executable and compiles the iOS arm64 bundle. Because upstream dependency
branches can change, a future production workflow should pin the exact SDL and MoltenVK commit IDs.

## Game data on the phone

The generated app bundle includes `image.bin` and `shaders.pack` derived by the build. It deliberately
does not include the game's data archives. Extract the data from your own legal copy on a PC, then
copy the resulting `data2` folder to the VT3 app's Documents folder using Apple's Files app:

`On My iPhone → VT3 → data2`

The runtime expects this directory to contain the game's `Resource` folder and associated data.

## Status and limitations

- iOS ARM64 build target, SDL3 app entry, MoltenVK integration, bundle resources, and Files-app game
  data location have been added.
- The project has not been built with Xcode in this development environment and has not been run on
  a physical iPhone. The first hosted build may expose toolchain or linker adjustments.
- A successfully compiled IPA is not proof of playable runtime compatibility. Graphics, audio,
  touch controls, app lifecycle, memory pressure, and frame rate must be verified on-device.
- An unsigned IPA cannot be installed directly without signing. The App Store is not part of this
  workflow.
