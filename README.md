# Packing Optimizer

This application provides a Tkinter-based GUI for experimenting with packing algorithms.

## Requirements
- Python 3.10+
- Tkinter (usually included with standard Python installs)
- matplotlib
- numpy
- pyyaml

Install the Python dependencies with:
```bash
pip install -r requirements.txt
```

## Running
Launch the interface by executing:
```bash
python main.py
```
The window opens with five tabs:

1. **Pakowanie 2D** – compare layouts of small boxes or bottles inside a chosen carton. Select a predefined carton or fill in your own dimensions. The tab shows vertical, horizontal and mixed layouts and lets you add air cushions.
2. **Pakowanie 3D** – find good carton sizes for a given product using a random search and the list of predefined cartons.
3. **Paletyzacja** – arrange cartons on a pallet by specifying pallet and box parameters. Choose layout variants, set the number of layers and centering options, then view totals such as stack height and required materials. The tab also features a **Tryb edycji** checkbox that lets you manually drag cartons on the pallet preview. Use **Shift+klik**, aby zaznaczyć wiele kartonów, a zaznaczone pola są podświetlane pomarańczową ramką. Available layouts are *column*, *interlock*, *l pattern*, *mixed* and *dense*. A new field lets you specify spacing between cartons to mimic looser palletizing. The interlock pattern is automatically chosen as the default whenever it is available.
    When centering cartons, the **Cała warstwa** mode centers the entire pattern as one block. In contrast, **Poszczególne obszary** centers every separate group of touching cartons individually. Cartons that only meet at their edges are considered separate groups.
4. **Materiały** – manage the catalogue of packaging materials. Add, edit or delete items together with their quantities, type, supplier and weight.
5. **Kartony** – edit predefined carton definitions, modify dimensions and weight or add your own carton codes for use in the other tabs.

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

