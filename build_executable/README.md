In order to use pyinstaller to build an FastAPI uvicorn executable, you need to follow these steps:

1. Install the pyinstaller pacakge inside virtual environment(.venv):

   If using uv, simply run:
   ```bash
   uv sync --with dev
   ```

   Or, if using regular pip with requirements.txt, run:
   ```bash
    pip install pyinstaller
    ```

2. Run command in project root directory:
    ```bash
    pyinstaller --onefile --name=LineBackupToDiscord --icon=./readme_imgs/logo.ico  --additional-hooks-dir .\extra_hooks\ main.py
    ```

3. Done! The executable will be created in the `dist` folder.