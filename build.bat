@echo off
echo Building...

pip install pyinstaller
pip install grapheme

pyinstaller --noconfirm --onefile --windowed ^
  --name "OCE" ^
  --icon "C:\Users\ysh20\Desktop\oc_editor_exe\icon.ico" ^
  --add-data "assets;assets" ^
  --add-data "version.json;." ^
  --hidden-import "customtkinter" ^
  --hidden-import "PIL" ^
  --hidden-import "sqlite3" ^
  main.py

pyinstaller --noconfirm --onefile --windowed ^
  --name "OCE_updater" ^
  updater_helper.py

echo Building installer...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

echo Done!
pause