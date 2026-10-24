CodeLens complete pack (replaces the earlier Upgrade Pack)
==========================================================
Contains everything added after Section 7: My files mode, the upload fix, the web page,
installable-app files, Docker + Render files, sample documents, README, LICENSE, CI files.

1. Stop the server if it runs (Ctrl + C).
2. Copy the folders and files of this pack INTO C:\Projects\CodeLens and choose "Replace".
   (Your own files that are not in the pack are not touched.)
3. Delete the old  web\icon.svg  if it exists.
4. Add these lines to .gitignore if they are not there:
       codelens_data/
       .codelens/
       demo/
5. pip install -r requirements-dev.txt
6. python -m pytest -q          -> expect 162 passed
7. python -m codelens serve --my-files
8. git add .   git commit -m "My files mode, demo mode, Docker and Render files"   git push

Then follow the guide PDF to put it on Render.
