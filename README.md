# Fayoum GP Plot Visualizer 📈

A custom Python desktop application built to streamline the analysis of Cadence transient simulation data. This tool parses standard `.vcsv` outputs to generate high-resolution, IEEE-standard graphics and eye diagrams, tailored for academic research and high-speed circuit design reports. 

> ⚠️ **Disclaimer:** This tool was developed as part of an engineering graduation project and is provided for **educational purposes only**.

## 🚀 Key Features

* **Cadence VCSV Parser:** Efficiently reads and structures complex transient simulation datasets.
* **IEEE-Standard Exports:** Generates publication-ready plots formatted to meet strict academic and industry standards.
* **Interactive Event Engine:** Allows users to mark, measure, and analyze signal data points directly on the graphical canvas.
* **Eye Diagram Generation:** Ideal for analyzing signal integrity in high-speed communication systems.
* **Dynamic GUI:** Built with Tkinter to provide a user-friendly interface for on-the-fly plot configuration.

## 📌 Important Notes for Users

* **Keyboard Shortcuts:** Please ensure your system's keyboard layout is set to **English** before using the software. The interactive shortcuts (for marking, measuring, etc.) will not function correctly if your keyboard is set to Arabic or another language layout.
* **Supported Files:** This version is specifically designed to parse standard Cadence `.vcsv` export formats.

## 🛠️ Required Libraries

If you are running the project from the source code, you will need to install the following Python packages:
* `matplotlib` (For rendering the high-quality plots)
* `numpy` (For handling the signal data arrays)
* *Note: `tkinter` is used for the GUI, but it comes pre-installed with standard Python on Windows.*

## 💻 Installation & Usage

### Option 1: Standalone Executable (Easiest for Students)
For immediate use without installing Python:
1. Navigate to the **Releases** section on the right side of this page.
2. Download `Fayoum_GP_Visualizer.exe`.
3. Run the application and load your `.vcsv` file.

### Option 2: Run from Source
To view or modify the code for your own learning:
1. Download or clone this repository.
2. Open your terminal or command prompt and install the dependencies:
   ```bash
   pip install matplotlib numpy
