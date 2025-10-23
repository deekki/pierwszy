# Packing Optimizer

Packing Optimizer is a toolkit for analysing carton and pallet configurations. It bundles
packing algorithms, sample material catalogues and a lightweight Tkinter interface for
quick experimentation.

## Requirements
- Python 3.10+
- Tkinter (usually included with standard Python installs)
- matplotlib
- numpy
- pyyaml
- rectpack

Install the Python dependencies with:
```bash
pip install -r requirements.txt
```

## Running
Launch the application with:
```bash
python main.py
```
The workspace contains five thematic tabs:

1. **Pakowanie 2D** – compare layouts of small products in a carton.
2. **Pakowanie 3D** – search for carton sizes that fit a product.
3. **Paletyzacja** – generate pallet layouts, review layer metrics and adjust arrangements.
4. **Materiały** – maintain the list of packaging materials with weights.
5. **Kartony** – edit predefined carton definitions used across the project.

## Pattern files
Custom pallet layouts saved from the GUI are stored as JSON files in
`packing_app/data/pallet_patterns`. When saving a pattern you will see the full
path in the confirmation message. Loading a pattern opens a file dialog pointed
to the same directory, so you can easily browse available definitions.

## Windows batch file
If you run the application by double-clicking the Python file, the console may close before you see any errors. You can create a `run_app.bat` file to keep the window open:
```bat
@echo off
cd /d "%~dp0"
python main.py
pause
```
Running this script from Explorer will show any error messages and wait for a key press before closing.

## Testing
Install the required packages before executing the test suite:
```bash
pip install -r requirements.txt
pytest
```

## License
This project is licensed under the [MIT License](LICENSE).

