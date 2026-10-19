# iOS port patch notes

This patch adds an experimental iOS ARM64 build path to the supplied VT3 source tree.

## Source changes

- `runtime/CMakeLists.txt`: adds a `VT3_IOS` application target linked against SDL3 and MoltenVK.
- `runtime/src/platform/ios_entry.m`: SDL/UIKit entry point, runtime environment setup, bundled resource loading, and Documents/data2 path.
- `runtime/src/input/input_sdl.c`: forwards normalized SDL touch events to the existing on-screen controller controls.
- `assets/ios/Info.plist`: iPhone-only app metadata, landscape orientation, and Files-app document sharing.
- `build.py`: adds `ios` build mode and packages an unsigned IPA while preserving bundle symlinks and executable file modes with `ditto`.
- `.github/workflows/ios-ipa.yml`: builds SDL3 and MoltenVK on a macOS runner, downloads the owner's supported executable from a configured secret URL, and uploads the IPA artifact.
- `ios/README.md` and `ios/PORTING_STATUS.md`: GitHub build and testing instructions.

## Verified locally

- Python syntax check passed for `build.py`.
- GitHub Actions workflow parsed as YAML.
- iOS Info.plist parsed as XML plist.
- Required target source/document files are present.

## Not verified locally

This environment is not macOS and has no Xcode/iOS SDK, so I could not compile the target, generate a genuine IPA, or test on iPhone. The first GitHub Actions run is an experimental device-build attempt and may need toolchain/linker fixes. A built unsigned IPA must be re-signed before installation and must be tested on a physical device before considering it playable.
