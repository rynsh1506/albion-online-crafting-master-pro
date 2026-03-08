# ⚔️ Albion Online - Crafting Master Pro

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

An advanced, multi-platform desktop application designed to help **Albion Online** players calculate exact crafting and refining profits. Built to match complex spreadsheet logic with a modern, user-friendly interface.

## ✨ Key Features

- **💯 Absolute Accuracy:** Core logic replicates exact in-game rounding mechanics (the notorious 997/998 resource return bug) ensuring your math is never off by a single silver.
- **📊 Smart Analytics:** Automatically calculates net material costs, station fees, profit per item, and suggests SRP (Suggested Retail Price) based on 5%-20% profit margins.
- **🎯 Focus Optimization:** Simulate crafts with or without Focus points to see the maximum yield and leftover Focus pool.
- **💾 Local History:** Automatically saves your last input state and calculation history locally—no data is lost when closing the app.
- **🌙 Modern UI:** Built with CustomTkinter, featuring a seamless Dark/Light mode toggle and a clean 5-column parameter dashboard.

## 🚀 Installation & Usage

### Running from Source

1. Clone this repository:

   ```bash
   git clone [https://github.com/rynsh1506/albion-online-crafting-master-pro.git](https://github.com/USERNAME_KAMU/albion-online-crafting-master-pro.git)
   ```

2. Navigate to the directory and install dependencies:

```bash
cd albion-online-crafting-master-pro
pip install -r requirements.txt
```

3. Run the application:

```bash
python main.py
```

## 📦 Building the Executable

If you want to compile the app into a standalone executable (e.g., `.exe` for Windows or a binary for Linux) without needing Python installed, you can use PyInstaller:

```bash
pip install pyinstaller
pyinstaller --noconsole --collect-all customtkinter main.py
```

_Note: Make sure to copy the logo images (`logo1.png` and `logo2.png`) into the generated `dist/main` folder so the UI renders correctly._

## 🛠️ Tech Stack

- **Language:** Python
- **GUI Framework:** CustomTkinter / Tkinter
- **Image Processing:** Pillow (PIL)
- **Data Persistence:** JSON (Local File)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
