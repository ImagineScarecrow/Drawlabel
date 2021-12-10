# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['__main__.py','__init__.py','label_file.py','pushbutton.py','shape.py',
'widgets\\brightness_contrast_dialog.py',
'widgets\\canvas.py',
'widgets\\color_dialog.py',
'widgets\\escapable_qlist_widget.py',
'widgets\\__init__.py',
'widgets\\label_dialog.py',
'widgets\\label_list_widget.py',
'widgets\\QProgressBar.py',
'widgets\\tool_bar.py',
'widgets\\unique_label_qlist_widget.py',
'widgets\\zoom_widget.py',
'utils\\image.py',
'utils\\__init__.py',
'utils\\_io.py',
'utils\\qt.py',
'utils\\shape.py',
],
             pathex=['C:\\Users\\jason.li\\DrawLabel_v0.6'],
             binaries=[],
             datas=[('config.json','.'),('labels.png','.')],
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,  
          [],
          name='DrawLabel_v0.6',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None ,
          icon = 'labels.ico')

