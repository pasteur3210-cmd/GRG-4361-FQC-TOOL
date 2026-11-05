from PyInstaller.utils.hooks import collect_submodules
a=Analysis(['main.py'],pathex=[],binaries=[],datas=[],hiddenimports=collect_submodules('keyring.backends'))
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,a.binaries,a.datas,[],name='GRG-4361 FQC Test Tool V1.0.7',debug=False,strip=False,upx=False,console=False)
