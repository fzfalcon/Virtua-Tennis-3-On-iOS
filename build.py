#!/usr/bin/env python3
"""Builds the game from your own copy of Virtua Tennis 3. Nothing game-derived is in this repo:
the translated code, the guest image and the shader pack are all generated here, from your VT3.exe.

Usage:
  python build.py android --exe VT3.exe            -> build/android/VT3-Android.apk   (macOS, Linux, Windows)
  python build.py macos   --exe VT3.exe --iso DISC  -> build/macos/VT3.app             (macOS only)
  python build.py ios     --exe VT3.exe             -> build/ios/VT3-iOS-unsigned.ipa  (macOS + Xcode)

VT3.exe is the English v1.0.1 executable without disc protection (a zip holding it also works).
DISC is the European PC DVD image; for Android the phone reads it at install time instead.
Toolchain locations come from ANDROID_HOME, ANDROID_NDK_HOME and JAVA_HOME (see README.md).
"""
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

REPO = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(REPO, "build")
SHADERS = os.path.join(REPO, "tools", "formats", "shaders")
IMAGE_SHA256 = "52be3cda5edb9aa536394fed656e22270d688d74e86db8602fd39a7512fc80bf"
WIN = os.name == "nt"


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd[:6]), "..." if len(cmd) > 6 else "")
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def need(tool, hint):
    if not shutil.which(tool):
        sys.exit("missing %s: %s" % (tool, hint))


def get_exe(path, out):
    """VT3.exe, bare or inside a zip, copied to out."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith("vt3.exe")]
            if not names:
                sys.exit("no VT3.exe in " + path)
            with open(out, "wb") as f:
                f.write(z.read(names[0]))
    else:
        shutil.copy(path, out)
    return out


def translate(exe):
    """VT3.exe -> build/game/vt3.c + image.bin, checked against the image the port was made from."""
    game = os.path.join(BUILD, "game")
    os.makedirs(game, exist_ok=True)
    src = get_exe(exe, os.path.join(game, "VT3.exe"))
    rc = os.path.join(REPO, "tools", "recomp")
    run([sys.executable, os.path.join(rc, "recomp.py"), src, "--out", game, "--name", "vt3",
         "--seeds", os.path.join(rc, "vt3_seeds.txt"), "--table-sizes", os.path.join(rc, "vt3_table_sizes.txt")])
    with open(os.path.join(game, "image.bin"), "rb") as f:
        if hashlib.sha256(f.read()).hexdigest() != IMAGE_SHA256:
            sys.exit("This VT3.exe is not the English v1.0.1 build the port supports.")
    return game


def shader_pack(exe):
    """The SPIR-V pack: every SM2 blob in VT3.exe plus the four rebuilt D3DX shaders, compiled with glslang."""
    need("glslangValidator", "install the Vulkan SDK (or the glslang package)")
    sys.path.insert(0, SHADERS)
    import scan_d3d9
    import gen_rebuilt_shaders
    import sm2_asm
    bins = os.path.join(BUILD, "shaders", "bin")
    rebuilt = os.path.join(BUILD, "shaders", "rebuilt")
    for d in (bins, rebuilt):
        os.makedirs(d, exist_ok=True)
    for _, r, _ in scan_d3d9.scan_file(exe):
        with open(os.path.join(bins, "%s.%s_%d_%d.bin" % (r["md5"], r["kind"], r["major"], r["minor"])), "wb") as f:
            f.write(r["blob"])
    for name, _src, _len, _entry, kind, consts, listing in gen_rebuilt_shaders.SHADERS:
        tokens, _ = sm2_asm.assemble(listing, consts)
        with open(os.path.join(rebuilt, "%s.%s_2_0.bin" % (name, "ps" if kind == "p" else "vs")), "wb") as f:
            f.write(b"".join(t.to_bytes(4, "little") for t in tokens))
    pack = os.path.join(BUILD, "shaders.pack")
    run([sys.executable, os.path.join(SHADERS, "gen_spirv_pack.py"), pack, "--bins", bins, "--bins", rebuilt])
    return pack


def android(exe):
    sys.path.insert(0, os.path.join(REPO, "android"))
    import build_apk
    need("cmake", "install CMake 3.22 or newer")
    need("ninja", "install Ninja")
    game = translate(exe)
    pack = shader_pack(os.path.join(game, "VT3.exe"))
    cm = os.path.join(BUILD, "android", "cmake")
    run(["cmake", "-S", os.path.join(REPO, "runtime"), "-B", cm, "-G", "Ninja",
         "-DCMAKE_TOOLCHAIN_FILE=" + os.path.join(build_apk.NDK, "build", "cmake", "android.toolchain.cmake"),
         "-DANDROID_PLATFORM=android-26", "-DANDROID_ABI=arm64-v8a", "-DCMAKE_BUILD_TYPE=Release",
         "-DVT3_GAME_DIR=" + game])
    print("Compiling the translated game. This takes 5 to 15 minutes.")
    run(["cmake", "--build", cm, "--target", "vt3android"])
    so = os.path.join(BUILD, "android", "libvt3android.so")
    run([build_apk.ndk_tool("llvm-strip"), "-o", so, os.path.join(cm, "libvt3android.so")])
    apk = build_apk.main(["build_apk.py", "game", "vt3android", "--so", so, "--asset", pack])
    out = os.path.join(BUILD, "android", "VT3-Android.apk")
    shutil.copy(apk, out)
    print("\nDone:", out)


def macos(exe, iso):
    if sys.platform != "darwin":
        sys.exit("The desktop build is macOS only. Use 'android' on Linux and Windows.")
    need("brew", "install Homebrew, then: brew install sdl3 molten-vk vulkan-loader vulkan-headers glslang")
    game = translate(exe)
    pack = shader_pack(os.path.join(game, "VT3.exe"))
    run([sys.executable, os.path.join(REPO, "tools", "recomp", "build_native.py"), game])
    data = os.path.expanduser("~/Library/Application Support/VT3/data2")
    if not os.path.isdir(os.path.join(data, "Resource")):
        if not iso:
            sys.exit("Pass --iso with your European PC DVD image the first time, to unpack the game data.")
        tool = os.path.join(BUILD, "macos", "vt3unpack")
        us = os.path.join(REPO, "android", "third_party", "unshield")
        os.makedirs(os.path.dirname(tool), exist_ok=True)
        lib = os.path.join(us, "lib")
        run(["clang", "-O2", "-DVT3_INSTALL_TEST", "-I", us, "-I", lib, "-o", tool,
             os.path.join(REPO, "android", "game", "jni", "install.c")]
            + [os.path.join(lib, f) for f in sorted(os.listdir(lib)) if f.endswith(".c")]
            + [os.path.join(lib, "md5", "md5c.c"), "-lz"])
        print("Unpacking the disc into", data)
        run([tool, iso, data])
    app_dir = os.path.join(BUILD, "macos")
    run(["bash", os.path.join(REPO, "assets", "macos", "make_app.sh"), os.path.join(game, "vt3_native"),
         os.path.join(game, "image.bin"), app_dir, data], env=dict(os.environ, VT3_SHADER_PACK=pack))
    print("\nDone:", os.path.join(app_dir, "VT3.app"))


def ios(exe):
    """Build an unsigned iOS IPA from the owner's supported executable and iOS dependencies."""
    if sys.platform != "darwin":
        sys.exit("The iOS build requires a macOS runner with Xcode.")
    need("cmake", "install CMake 3.22 or newer")
    need("xcodebuild", "install Xcode and select it with xcode-select")
    need("glslangValidator", "install glslang (brew install glslang)")
    sdl3_dir = os.environ.get("SDL3_DIR")
    molten_framework = os.environ.get("VT3_MOLTENVK_FRAMEWORK")
    molten_include = os.environ.get("VT3_MOLTENVK_INCLUDE_DIR")
    if not sdl3_dir or not os.path.isdir(sdl3_dir):
        sys.exit("Set SDL3_DIR to the CMake package directory for the iOS SDL3 build.")
    if not molten_framework or not os.path.isfile(os.path.join(molten_framework, "MoltenVK")):
        sys.exit("Set VT3_MOLTENVK_FRAMEWORK to the ios-arm64/MoltenVK.framework directory.")
    if not molten_include or not os.path.isfile(os.path.join(molten_include, "vulkan", "vulkan.h")):
        sys.exit("Set VT3_MOLTENVK_INCLUDE_DIR to the Vulkan headers directory.")

    game = translate(exe)
    pack = shader_pack(os.path.join(game, "VT3.exe"))
    cm = os.path.join(BUILD, "ios", "cmake")
    run(["cmake", "-S", os.path.join(REPO, "runtime"), "-B", cm, "-G", "Xcode",
         "-DCMAKE_SYSTEM_NAME=iOS", "-DCMAKE_OSX_SYSROOT=iphoneos",
         "-DCMAKE_OSX_ARCHITECTURES=arm64", "-DCMAKE_OSX_DEPLOYMENT_TARGET=15.0",
         "-DCMAKE_BUILD_TYPE=Release", "-DVT3_IOS=ON", "-DVT3_GAME_DIR=" + game,
         "-DVT3_SHADER_PACK=" + pack, "-DSDL3_DIR=" + sdl3_dir,
         "-DVT3_MOLTENVK_FRAMEWORK=" + molten_framework,
         "-DVT3_MOLTENVK_INCLUDE_DIR=" + molten_include,
         "-DVT3_MOLTENVK_DYNAMIC=" + ("ON" if os.environ.get("VT3_MOLTENVK_DYNAMIC") == "1" else "OFF")])
    print("Compiling translated game for iOS arm64. This can take a long time.")
    run(["cmake", "--build", cm, "--config", "Release", "--target", "vt3ios", "--parallel", str(os.cpu_count() or 2)])

    apps = []
    for root, dirs, _files in os.walk(cm):
        for d in list(dirs):
            if d == "VT3.app":
                apps.append(os.path.join(root, d))
                dirs.remove(d)
    if not apps:
        sys.exit("Build completed without producing VT3.app; inspect the Xcode build log.")
    app_src = apps[0]
    out_dir = os.path.join(BUILD, "ios")
    app_out = os.path.join(out_dir, "VT3.app")
    if os.path.exists(app_out):
        shutil.rmtree(app_out)
    shutil.copytree(app_src, app_out, symlinks=True)
    # iOS bundle resources live at the .app root (not macOS Contents/Resources).
    shutil.copy2(os.path.join(game, "image.bin"), os.path.join(app_out, "image.bin"))
    shutil.copy2(pack, os.path.join(app_out, "shaders.pack"))
    # This is intentionally an unsigned IPA so users can sign it with their own Apple ID using
    # AltStore/Sideloadly. A sideloading utility must re-sign it before installation.
    payload = os.path.join(out_dir, "Payload")
    if os.path.exists(payload):
        shutil.rmtree(payload)
    os.makedirs(payload)
    shutil.copytree(app_out, os.path.join(payload, "VT3.app"), symlinks=True)
    ipa = os.path.join(out_dir, "VT3-iOS-unsigned.ipa")
    if os.path.exists(ipa): os.remove(ipa)
    # Apple's ditto preserves executable modes, symlinks and framework bundle structure in an IPA.
    run(["ditto", "-c", "-k", "--sequesterRsrc", "Payload", os.path.basename(ipa)], cwd=out_dir)
    shutil.rmtree(payload)
    print("\nDone:", ipa)
    print("Unsigned IPA: sign it with your Apple ID before installing on iPhone.")


def main(argv):
    if len(argv) < 2 or argv[1] not in ("android", "macos", "ios") or "--exe" not in argv:
        print(__doc__)
        return 2
    exe = os.path.abspath(argv[argv.index("--exe") + 1])
    iso = os.path.abspath(argv[argv.index("--iso") + 1]) if "--iso" in argv else None
    try:
        import pefile, capstone  # noqa: F401  (recomp.py needs both)
    except ImportError:
        sys.exit("missing Python packages: pip install pefile capstone")
    if argv[1] == "android":
        android(exe)
    elif argv[1] == "ios":
        ios(exe)
    else:
        macos(exe, iso)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
