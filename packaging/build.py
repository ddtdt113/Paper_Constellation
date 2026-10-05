"""Build a standalone Paper Constellation app with PyInstaller and pack it for a release.

    pip install . pyinstaller
    python packaging/build.py            # build + archive into dist/
    python packaging/build.py --smoke    # run the built app's self-test

Produces dist/PaperConstellation-<version>-<OS>-<arch>.zip (macOS, Windows) or .tar.gz (Linux).
The app is built in one-folder mode so the bundled Qt (LGPL-3.0) libraries stay replaceable.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from paper_constellation import __version__  # noqa: E402

NAME = "Paper Constellation"
DIST = ROOT / "dist"
# Qt modules the app never imports; keeping them out shrinks the download a lot
EXCLUDES = ["PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.QtWebEngineCore",
            "PySide6.QtWebEngineWidgets", "PySide6.QtMultimedia", "PySide6.Qt3DCore", "PySide6.QtPdf",
            "PySide6.QtCharts", "PySide6.QtDataVisualization", "tkinter"]


def platform_tag() -> str:
    os_name = {"darwin": "macOS", "win32": "Windows"}.get(sys.platform, "Linux")
    machine = platform.machine().lower()
    arch = {"x86_64": "x64", "amd64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(machine, machine)
    return f"{os_name}-{arch}"


BASE = f"PaperConstellation-{__version__}-{platform_tag()}"
STAGE = DIST / BASE


def executable() -> Path:
    if sys.platform == "darwin":
        return STAGE / f"{NAME}.app" / "Contents" / "MacOS" / NAME
    if sys.platform == "win32":
        return STAGE / NAME / f"{NAME}.exe"
    return STAGE / NAME / NAME


def build() -> Path:
    shutil.rmtree(DIST, ignore_errors=True)
    shutil.rmtree(ROOT / "build", ignore_errors=True)
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--onedir",
           "--name", NAME, "--paths", str(ROOT / "src"),
           "--collect-data", "paper_constellation",
           "--osx-bundle-identifier", "io.github.ddtdt113.paperconstellation",
           "--specpath", str(ROOT / "build")]
    for m in EXCLUDES:
        cmd += ["--exclude-module", m]
    cmd.append(str(ROOT / "packaging" / "launcher.py"))
    subprocess.run(cmd, check=True, cwd=ROOT)

    built = DIST / (f"{NAME}.app" if sys.platform == "darwin" else NAME)
    STAGE.mkdir()
    shutil.move(str(built), str(STAGE / built.name))
    for f in [ROOT / "LICENSE", ROOT / "NOTICE", *sorted((ROOT / "packaging" / "licenses").glob("*.txt"))]:
        shutil.copy(f, STAGE / f.name)
    shutil.copy(ROOT / "packaging" / "README-binary.txt", STAGE / "README.txt")

    if sys.platform == "darwin":
        out = DIST / f"{BASE}.zip"   # ditto keeps the symlinks inside the .app bundle intact
        subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(STAGE), str(out)], check=True)
    elif sys.platform == "win32":
        out = Path(shutil.make_archive(str(DIST / BASE), "zip", DIST, BASE))
    else:
        out = Path(shutil.make_archive(str(DIST / BASE), "gztar", DIST, BASE))
    print(f"built {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return out


def smoke() -> None:
    exe = executable()
    env = dict(os.environ)
    if sys.platform.startswith("linux"):
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
    r = subprocess.run([str(exe), "--self-test"], env=env, timeout=180)
    if r.returncode != 0:
        sys.exit(f"self-test failed with exit code {r.returncode}")
    print(f"self-test passed: {exe}")


if __name__ == "__main__":
    smoke() if "--smoke" in sys.argv else build()
