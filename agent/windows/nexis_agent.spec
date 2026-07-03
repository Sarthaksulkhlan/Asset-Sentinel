# Build with:
#   pyinstaller agent/windows/nexis_agent.spec
#
# Output:
#   dist/NEXIS Agent.exe
#
# Place a configured .env beside the executable before running it as Administrator.

block_cipher = None

a = Analysis(
    ["agent/windows/asset_sentinel_service.py"],
    pathex=["."],
    binaries=[],
    datas=[
        (".env.example", "."),
        ("database/schemas/schema.sql", "database/schemas"),
    ],
    hiddenimports=[
        "bcrypt",
        "jwt",
        "psycopg2",
        "pythoncom",
        "servicemanager",
        "win32event",
        "win32evtlog",
        "win32service",
        "win32serviceutil",
        "win32timezone",
        "wmi",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="NEXIS Agent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
