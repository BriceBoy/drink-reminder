from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

root = Path(SPECPATH)
datas, binaries, hiddenimports = collect_all("windows_toasts")
hiddenimports += collect_submodules("winrt")
hiddenimports += ["pystray._win32", "PIL.IcoImagePlugin", "PIL.PngImagePlugin"]
datas += [(str(root / "water_reminder" / "assets"), "water_reminder/assets")]

a = Analysis(
    [str(root / "run.pyw")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="WaterReminder",
    console=False,
    icon=str(root / "water_reminder" / "assets" / "water.ico"),
    upx=False,
)
