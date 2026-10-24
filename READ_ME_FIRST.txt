CodeLens upgrade: "My files" mode, upload fix, installable app
==============================================================

1. Close the server if it is running (Ctrl + C in its terminal).
2. Copy the folders of this pack INTO C:\Projects\CodeLens and choose "Replace" when asked.
   The paths inside the pack match your project: codelens\..., web\..., tests\..., .github\...
3. Delete the old file  web\icon.svg  (it is replaced by three PNG icons).
4. No new libraries are needed. Run:  python -m pytest -q      (expect 154 passed)
5. Start it:  python -m codelens serve --my-files
   Open http://127.0.0.1:8000, create an account (first time), and type a word you remember.
6. Add this line to .gitignore if it is not there:  codelens_data/
   Then:  git add .   git commit -m "My files mode, upload fix, installable app"   git push

The guide PDF (CodeLens_Upgrade_My_Files_and_Install.pdf) explains every change.
