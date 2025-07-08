# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import os

def recursive_datas(path):
    result = []
    for p in Path(path).rglob('*'):
        if p.is_file():
            source = str(p)
            relative_parent = str(p.relative_to(path).parent)
            
            # Prepend "assets" to all destination paths
            if relative_parent == '.':
                dest_dir = 'assets'
            else:
                dest_dir = f'assets/{relative_parent}'
            
            result.append((source, dest_dir))
    return result

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=recursive_datas('assets'),
    hiddenimports=['_cffi_backend', 'coincurve._cffi_backend'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [('v', None, 'OPTION')],
    exclude_binaries=True,
    name='main',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main',
)
