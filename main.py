import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.ticker import MultipleLocator
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Disable default Matplotlib keymaps that conflict with our custom shortcuts
plt.rcParams['keymap.home'].clear()
plt.rcParams['keymap.back'].clear()
plt.rcParams['keymap.save'].clear()
plt.rcParams['keymap.pan'].clear()

# ==========================================
# 1. IEEE ACADEMIC FORMATTING STANDARDS
# ==========================================
plt.rcParams.update({
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'Computer Modern Roman', 'DejaVu Serif'],
    'axes.labelsize': 12,
    'axes.titlesize': 12,
    'font.size': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'axes.linewidth': 1.0,
    'grid.linewidth': 0.5,
    'grid.alpha': 0.5,
    'figure.dpi': 120, 
})

PUB_BLUE = '#0072BD'
PALETTE_GRAY = ['#000000', '#333333', '#555555', '#777777', '#222222', '#444444', '#666666', '#888888']
PALETTE_COLOR = ['#0072BD', '#D95319', '#EDB120', '#7E2F8E', '#77AC30', '#4DBEEE', '#A2142F', '#000000']
STANDARD_COLORS = ['blue', 'orange', 'green', 'red', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan', 'black']

# ==========================================
# 2. CUSTOM TOOLBAR
# ==========================================
class CustomToolbar(NavigationToolbar2Tk):
    def __init__(self, canvas, window, export_callback):
        self.export_callback = export_callback
        super().__init__(canvas, window)
        
    def save_figure(self, *args):
        self.export_callback()

# ==========================================
# 3. APPLICATION CLASS
# ==========================================
class UniversalIEEEPlotterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fayoum GP Plot Visualizer V2.3.1")
        
        self.geometry("1100x750")
        try:
            self.state('zoomed')
        except:
            pass 
        
        self.raw_data = [] 
        self.file_loaded = False
        
        # State trackers
        self.markers = []
        self.undo_stack = []  
        
        self.pt_A_coords = None
        self.pt_B_coords = None
        self.pt_R_coords = None
        self.pt_D_coords = None
        self.pt_A_artists = []
        self.pt_B_artists = []
        self.pt_R_artists = []
        self.pt_D_artists = []
        self.delta_line_artist = None
        self.delta_text_artist = None
        self.delta_line_artist_RD = None
        self.delta_text_artist_RD = None
        
        self.trace_vars = [] 

        self._build_menus()
        self._build_ui()
        self._setup_global_shortcuts()

    def _build_menus(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Generate Plot (Ctrl+P)", command=self.generate_plot)
        file_menu.add_command(label="Export High-Res IEEE Plot (Ctrl+S)", command=self.export_plot)
        file_menu.add_command(label="Clear All Markers & Deltas", command=self.clear_markers)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Interactive Shortcuts Guide", command=self.show_shortcuts)
        menubar.add_cascade(label="Help", menu=help_menu)

    def show_shortcuts(self):
        cheat_sheet = (
            "--- GLOBAL SHORTCUTS ---\n"
            "[ Ctrl + P ] - Generate / Refresh Plot\n"
            "[ Ctrl + S ] - Export High-Res Plot\n\n"
            "--- GRAPH INTERACTION SHORTCUTS ---\n"
            "(Hover mouse anywhere over the right panel)\n\n"
            "[ Right-Click ] - Drop Permanent Marker\n"
            "[ P ] - Generate Plot\n"
            "[ S ] - Export Plot\n"
            "[ C ] - Clear All Markers & Measurements\n"
            "[ U ] - Undo Last Placed Point (Marker, A, B, R, or D)\n"
            "[ A ] - Drop Delta Measure Point A\n"
            "[ B ] - Drop Delta Measure Point B\n"
            "[ R ] - Drop Delta Measure Point R\n"
            "[ D ] - Drop Delta Measure Point D\n"
        )
        messagebox.showinfo("Shortcuts Guide", cheat_sheet)

    def _setup_global_shortcuts(self):
        self.bind_all('<Control-p>', self.generate_plot)
        self.bind_all('<Control-P>', self.generate_plot)
        self.bind_all('<Control-s>', self.export_plot)
        self.bind_all('<Control-S>', self.export_plot)

    def _build_ui(self):
        # --- LEFT PANEL (Bulletproof Scroll Engine) ---
        left_container = ttk.Frame(self, width=350)
        left_container.pack(side=tk.LEFT, fill=tk.Y)
        left_container.pack_propagate(False)
        
        self.left_canvas = tk.Canvas(left_container, highlightthickness=0)
        self.left_scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=self.left_canvas.yview)
        
        self.left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.control_frame = ttk.Frame(self.left_canvas, padding=(10, 10, 10, 30))
        
        self.control_frame.bind("<Configure>", lambda e: self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all")))
        self.left_canvas.create_window((0, 0), window=self.control_frame, anchor="nw", width=330)
        self.left_canvas.configure(yscrollcommand=self.left_scrollbar.set)
        
        def _on_mousewheel(event):
            if event.num == 4 or getattr(event, 'delta', 0) > 0:
                self.left_canvas.yview_scroll(-1, "units")
            elif event.num == 5 or getattr(event, 'delta', 0) < 0:
                self.left_canvas.yview_scroll(1, "units")

        def _bind_mousewheel(e):
            self.left_canvas.bind_all("<MouseWheel>", _on_mousewheel)
            self.left_canvas.bind_all("<Button-4>", _on_mousewheel) 
            self.left_canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(e):
            self.left_canvas.unbind_all("<MouseWheel>")
            self.left_canvas.unbind_all("<Button-4>")
            self.left_canvas.unbind_all("<Button-5>")

        self.left_canvas.bind("<Enter>", _bind_mousewheel)
        self.left_canvas.bind("<Leave>", _unbind_mousewheel)

        # 1. LOAD DATA
        ttk.Label(self.control_frame, text="1. Load Data", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0,5))
        ttk.Button(self.control_frame, text="Load VCSV File", command=self.load_file).pack(fill=tk.X)
        self.lbl_filename = ttk.Label(self.control_frame, text="No file loaded", foreground="gray", wraplength=280)
        self.lbl_filename.pack(anchor=tk.W, pady=(5, 10))

        # 2. PLOT SETTINGS
        ttk.Label(self.control_frame, text="2. Plot Settings", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0,5))
        
        ttk.Label(self.control_frame, text="Plot Type:").pack(anchor=tk.W)
        self.mode_var = tk.StringVar(value="Standard Plot (AC/DC/Tran)")
        self.mode_cb = ttk.Combobox(self.control_frame, textvariable=self.mode_var, values=["Eye Diagram", "Standard Plot (AC/DC/Tran)"], state="readonly")
        self.mode_cb.pack(fill=tk.X, pady=(0, 5))
        self.mode_cb.bind("<<ComboboxSelected>>", self._on_mode_change)

        ttk.Label(self.control_frame, text="Data Rate (Gb/s) [Eye Only]:").pack(anchor=tk.W)
        self.rate_var = tk.StringVar(value="24")
        self.rate_entry = ttk.Entry(self.control_frame, textvariable=self.rate_var)
        self.rate_entry.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(self.control_frame, text="X-Axis Scale Multiplier:").pack(anchor=tk.W)
        self.scale_var = tk.StringVar(value="1") 
        ttk.Entry(self.control_frame, textvariable=self.scale_var).pack(fill=tk.X, pady=(0, 5))

        ttk.Label(self.control_frame, text="Y-Axis Scale Multiplier:").pack(anchor=tk.W)
        self.yscale_var = tk.StringVar(value="1") 
        ttk.Entry(self.control_frame, textvariable=self.yscale_var).pack(fill=tk.X, pady=(0, 5))

        ttk.Label(self.control_frame, text="Plot Title:").pack(anchor=tk.W)
        self.title_var = tk.StringVar(value="")
        ttk.Entry(self.control_frame, textvariable=self.title_var).pack(fill=tk.X, pady=(0, 5))

        ttk.Label(self.control_frame, text="X-Axis Label:").pack(anchor=tk.W)
        self.xlabel_var = tk.StringVar(value="X-Axis")
        ttk.Entry(self.control_frame, textvariable=self.xlabel_var).pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(self.control_frame, text="Y-Axis Label:").pack(anchor=tk.W)
        self.ylabel_var = tk.StringVar(value="Y-Axis")
        ttk.Entry(self.control_frame, textvariable=self.ylabel_var).pack(fill=tk.X, pady=(0, 5))

        self.logx_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.control_frame, text="Logarithmic X-Axis (For AC)", variable=self.logx_var).pack(anchor=tk.W, pady=(0, 10))

        # 3. CURVE STYLING
        ttk.Label(self.control_frame, text="3. Curve Styling", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0,5))
        
        ttk.Label(self.control_frame, text="Color Theme:").pack(anchor=tk.W)
        self.theme_var = tk.StringVar(value="Modern Color (MATLAB)")
        self.theme_cb = ttk.Combobox(self.control_frame, textvariable=self.theme_var, values=["Classic Grayscale", "Modern Color (MATLAB)", "Custom (Per Trace)"], state="readonly")
        self.theme_cb.pack(fill=tk.X, pady=(0, 5))
        self.theme_cb.bind("<<ComboboxSelected>>", self._on_theme_change)

        ttk.Label(self.control_frame, text="Line Style:").pack(anchor=tk.W)
        self.linestyle_var = tk.StringVar(value="All Solid")
        self.style_cb = ttk.Combobox(self.control_frame, textvariable=self.linestyle_var, values=["Mixed (Solid/Dash/Dot)", "All Solid"], state="readonly")
        self.style_cb.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(self.control_frame, text="Line Thickness:").pack(anchor=tk.W)
        self.linewidth_var = tk.StringVar(value="3")
        self.linewidth_entry = ttk.Entry(self.control_frame, textvariable=self.linewidth_var)
        self.linewidth_entry.pack(fill=tk.X, pady=(0, 10))

        # 4. TRACE LABELS & COLORS 
        ttk.Label(self.control_frame, text="4. Trace Configuration", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0,5))
        
        header_frame = ttk.Frame(self.control_frame)
        header_frame.pack(fill=tk.X)
        ttk.Label(header_frame, text="Trace Name", width=18).pack(side=tk.LEFT, padx=(20, 2)) 
        ttk.Label(header_frame, text="Color", width=10).pack(side=tk.LEFT)
        
        self.trace_manager_frame = ttk.Frame(self.control_frame)
        self.trace_manager_frame.pack(fill=tk.X, pady=(0, 10))

        # 5. AXIS LIMITS & TICKS
        ttk.Label(self.control_frame, text="5. Limits & Ticks", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0,5))
        
        limits_frame = ttk.Frame(self.control_frame)
        limits_frame.pack(fill=tk.X, pady=(0, 25))
        
        ttk.Label(limits_frame, text="X Min:").grid(row=0, column=0, sticky=tk.W)
        self.xmin_var = tk.StringVar()
        ttk.Entry(limits_frame, textvariable=self.xmin_var, width=10).grid(row=0, column=1, padx=2)
        ttk.Label(limits_frame, text="X Max:").grid(row=0, column=2, sticky=tk.W)
        self.xmax_var = tk.StringVar()
        ttk.Entry(limits_frame, textvariable=self.xmax_var, width=10).grid(row=0, column=3, padx=2)

        ttk.Label(limits_frame, text="Y Min:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.ymin_var = tk.StringVar()
        ttk.Entry(limits_frame, textvariable=self.ymin_var, width=10).grid(row=1, column=1, padx=2, pady=5)
        ttk.Label(limits_frame, text="Y Max:").grid(row=1, column=2, sticky=tk.W, pady=5)
        self.ymax_var = tk.StringVar()
        ttk.Entry(limits_frame, textvariable=self.ymax_var, width=10).grid(row=1, column=3, padx=2, pady=5)

        ttk.Label(limits_frame, text="X Step:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.xstep_var = tk.StringVar()
        ttk.Entry(limits_frame, textvariable=self.xstep_var, width=10).grid(row=2, column=1, padx=2, pady=5)
        ttk.Label(limits_frame, text="Y Step:").grid(row=2, column=2, sticky=tk.W, pady=5)
        self.ystep_var = tk.StringVar() 
        ttk.Entry(limits_frame, textvariable=self.ystep_var, width=10).grid(row=2, column=3, padx=2, pady=5)

        # --- RIGHT PANEL (Matplotlib Canvas) ---
        plot_frame = ttk.Frame(self)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.fig, self.ax = plt.subplots(figsize=(8, 5))
        self.ax.set_title("Waiting for data...")
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        
        self.plot_canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.plot_canvas.draw()
        
        # --- FIX 1: Smart Focus ---
        # Politer focus handling. Only activates canvas shortcuts if you aren't currently typing in an input field.
        self.plot_canvas.get_tk_widget().configure(takefocus=True)
        def _smart_focus(event):
            current_focus = self.focus_get()
            if not isinstance(current_focus, (tk.Entry, ttk.Entry, ttk.Combobox)):
                self.plot_canvas.get_tk_widget().focus_set()
        self.plot_canvas.get_tk_widget().bind("<Enter>", _smart_focus)
        
        self.plot_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.toolbar = CustomToolbar(self.plot_canvas, plot_frame, self.export_plot)
        self.toolbar.update()
        
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
        btn_plot = ttk.Button(self.toolbar, text="▶ Generate Plot", command=self.generate_plot)
        btn_plot.pack(side=tk.LEFT, padx=2)
        btn_clear = ttk.Button(self.toolbar, text="✖ Clear Markers", command=self.clear_markers)
        btn_clear.pack(side=tk.LEFT, padx=2)

        self._on_mode_change(None)

    def _on_theme_change(self, event=None):
        theme = self.theme_var.get()
        cb_state = "readonly" if theme == "Custom (Per Trace)" else "disabled"
        for trace in self.trace_vars:
            if 'color_cb' in trace:
                trace['color_cb'].configure(state=cb_state)

    def _on_mode_change(self, event):
        state_toggle = "readonly" if self.mode_var.get() == "Standard Plot (AC/DC/Tran)" else "disabled"
        entry_toggle = "normal" if self.mode_var.get() == "Standard Plot (AC/DC/Tran)" else "disabled"
        
        if self.mode_var.get() == "Standard Plot (AC/DC/Tran)":
            self.rate_entry.configure(state="disabled")
            if self.linewidth_var.get() == "0.5": self.linewidth_var.set("3")
        else:
            self.rate_entry.configure(state="normal")
            if self.linewidth_var.get() == "3": self.linewidth_var.set("0.5")
            
        self.theme_cb.configure(state="readonly")
        self.style_cb.configure(state=state_toggle)
        self.linewidth_entry.configure(state="normal")
        
        for child in self.trace_manager_frame.winfo_children():
            for widget in child.winfo_children():
                try: widget.configure(state="normal")
                except: pass

        if self.mode_var.get() == "Standard Plot (AC/DC/Tran)":
            self._on_theme_change(None)

    # --- Trace Manager Drag and Drop Methods ---
    def _start_trace_drag(self, event):
        handle = event.widget
        row_frame = handle.master
        for i, trace in enumerate(self.trace_vars):
            if trace['frame'] == row_frame:
                self._drag_data = {'start_y': event.y_root, 'index': i, 'frame': row_frame}
                break

    def _do_trace_drag(self, event):
        if not hasattr(self, '_drag_data'): return
        current_idx = self._drag_data['index']
        
        row_height = self._drag_data['frame'].winfo_height()
        if row_height < 10: row_height = 25
        
        delta_y = event.y_root - self._drag_data['start_y']
        move_count = int(delta_y // row_height)
        
        if move_count != 0:
            new_idx = current_idx + move_count
            new_idx = max(0, min(new_idx, len(self.trace_vars) - 1))
            
            if new_idx != current_idx:
                item = self.trace_vars.pop(current_idx)
                self.trace_vars.insert(new_idx, item)
                
                for trace in self.trace_vars:
                    trace['frame'].pack_forget()
                for trace in self.trace_vars:
                    trace['frame'].pack(fill=tk.X, pady=2)
                    
                self._drag_data['index'] = new_idx
                self._drag_data['start_y'] = event.y_root

    def _stop_trace_drag(self, event):
        if hasattr(self, '_drag_data'):
            del self._drag_data

    def load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Cadence VCSV", "*.vcsv"), ("All Files", "*.*")])
        if not filepath: return
        
        filename_ext = os.path.basename(filepath)
        filename_no_ext = os.path.splitext(filename_ext)[0]
        
        self.lbl_filename.config(text=filename_ext)
        self.title_var.set(filename_no_ext)
        self.update_idletasks()
        
        try:
            with open(filepath, 'r') as f: lines = f.readlines()
            data_start = next(i for i, line in enumerate(lines) if self._is_float(line.split(',')[0]))
            
            x_var_name, y_var_name = "X-Axis", "Y-Axis"
            x_unit, y_unit = "", ""
            
            if data_start >= 2:
                try:
                    # VCSV places names two lines above the data
                    var_line = lines[data_start-2].split(',')
                    if len(var_line) >= 2:
                        x_var_name = var_line[0].strip(' ;"\n')
                        y_var_name = var_line[1].strip(' ;"\n')
                    
                    # VCSV places units one line above the data
                    unit_line = lines[data_start-1].split(',')
                    if len(unit_line) >= 2:
                        x_unit = unit_line[0].strip(' ;"\n')
                        y_unit = unit_line[1].strip(' ;"\n')
                except Exception:
                    pass
            
            raw_headers = []
            for i in range(data_start):
                line = lines[i].strip()
                if not line or 'Version' in line or 'X, Y' in line or 'Re, Re' in line or 'xunit' in line or 'temperature, Y' in line:
                    continue
                if line.startswith(';'):
                    parts = line.split(',')
                    names = [p.strip(' ;"\n') for p in parts if p.strip(' ;"\n')]
                    if names:
                        raw_headers = names
                        break

            df = pd.read_csv(filepath, skiprows=data_start, header=None)
            df = df.apply(pd.to_numeric, errors='coerce')
            
            self.raw_data = [] 
            extracted_names = []
            
            max_x = 0.0
            max_y = 0.0
            
            for i in range(0, df.shape[1], 2):
                if i+1 < df.shape[1]:
                    pair = df.iloc[:, [i, i+1]].dropna()
                    
                    x_arr = pair.iloc[:, 0].values
                    y_arr = pair.iloc[:, 1].values
                    
                    if len(x_arr) > 0: max_x = max(max_x, np.max(np.abs(x_arr)))
                    if len(y_arr) > 0: max_y = max(max_y, np.max(np.abs(y_arr)))
                    
                    self.raw_data.append((x_arr, y_arr))
                    
                    header_idx = i // 2
                    if header_idx < len(raw_headers) and raw_headers[header_idx]: 
                        extracted_names.append(raw_headers[header_idx])
                    else: 
                        extracted_names.append(f"Trace {header_idx+1}")

            def get_best_scale(val, base_unit):
                if val == 0 or np.isnan(val) or np.isinf(val) or val >= 1: 
                    return "1", base_unit
                prefixes = {1e3: "m", 1e6: "µ", 1e9: "n", 1e12: "p", 1e15: "f"}
                for mult, pref in prefixes.items():
                    if val * mult >= 0.5:
                        new_unit = pref + base_unit if base_unit else pref
                        mult_str = f"1e{int(math.log10(mult))}" if mult >= 1e6 else str(int(mult))
                        return mult_str, new_unit
                return "1", base_unit

            x_mult, new_x_unit = get_best_scale(max_x, x_unit)
            y_mult, new_y_unit = get_best_scale(max_y, y_unit)

            self.scale_var.set(x_mult)
            self.yscale_var.set(y_mult)
            
            final_x_label = f"{x_var_name} ({new_x_unit})" if new_x_unit else x_var_name
            final_y_label = f"{y_var_name} ({new_y_unit})" if new_y_unit else y_var_name
            
            self.xlabel_var.set(final_x_label if final_x_label else "X-Axis")
            self.ylabel_var.set(final_y_label if final_y_label else "Y-Axis")

            for widget in self.trace_manager_frame.winfo_children():
                widget.destroy()
                
            self.trace_vars = []
            for i, name in enumerate(extracted_names):
                row_frame = ttk.Frame(self.trace_manager_frame)
                row_frame.pack(fill=tk.X, pady=2)
                
                handle = ttk.Label(row_frame, text="☰", cursor="fleur", foreground="gray")
                handle.pack(side=tk.LEFT, padx=(2, 5))
                handle.bind("<Button-1>", self._start_trace_drag)
                handle.bind("<B1-Motion>", self._do_trace_drag)
                handle.bind("<ButtonRelease-1>", self._stop_trace_drag)
                
                n_var = tk.StringVar(value=name)
                ttk.Entry(row_frame, textvariable=n_var, width=20).pack(side=tk.LEFT, padx=(0, 5))
                
                c_var = tk.StringVar(value=STANDARD_COLORS[i % len(STANDARD_COLORS)])
                cb = ttk.Combobox(row_frame, textvariable=c_var, values=STANDARD_COLORS, width=12)
                cb.pack(side=tk.LEFT)
                
                self.trace_vars.append({'name': n_var, 'color': c_var, 'color_cb': cb, 'frame': row_frame})

            self._on_mode_change(None) 
            self._on_theme_change(None)
            self.file_loaded = True
            
            self.control_frame.update_idletasks()
            self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all"))
            
            self.generate_plot()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse file: {e}")

    def _is_float(self, string):
        try: float(string); return True
        except ValueError: return False

    def generate_plot(self, event=None):
        if not self.file_loaded:
            messagebox.showwarning("No Data", "Please load a VCSV file first.")
            return

        self.clear_markers()
        self.ax.clear()
        
        try:
            scale = float(self.scale_var.get())
            yscale = float(self.yscale_var.get())
        except ValueError:
            messagebox.showerror("Input Error", "Scale Multipliers must be valid numbers.")
            return
            
        if self.mode_var.get() == "Eye Diagram":
            success = self._draw_eye(scale, yscale)
            if not success: return 
        else:
            self._draw_standard(scale, yscale)

        title_text = self.title_var.get().strip()
        if title_text: self.ax.set_title(title_text)
        
        self.ax.set_xlabel(self.xlabel_var.get())
        self.ax.set_ylabel(self.ylabel_var.get())
        
        self.ax.grid(True, linestyle='-', alpha=0.3, which='both')
        
        try:
            if self.xmin_var.get(): self.ax.set_xlim(left=float(self.xmin_var.get()))
            if self.xmax_var.get(): self.ax.set_xlim(right=float(self.xmax_var.get()))
            if self.ymin_var.get(): self.ax.set_ylim(bottom=float(self.ymin_var.get()))
            if self.ymax_var.get(): self.ax.set_ylim(top=float(self.ymax_var.get()))
        except ValueError:
            pass

        try:
            if self.ystep_var.get():
                ystep = float(self.ystep_var.get())
                self.ax.yaxis.set_major_locator(MultipleLocator(ystep))
            if self.xstep_var.get():
                if not (self.mode_var.get() == "Standard Plot (AC/DC/Tran)" and self.logx_var.get()):
                    xstep = float(self.xstep_var.get())
                    self.ax.xaxis.set_major_locator(MultipleLocator(xstep))
        except ValueError:
            pass

        self.fig.tight_layout()
        self.plot_canvas.draw_idle()
        
        self.toolbar.update()
        self.toolbar._nav_stack.clear()
        self.toolbar.push_current()
        
        self._setup_interactions()

    # ==========================================
    # INTERACTIVE CLICK-TO-MARK ENGINE V2.4
    # ==========================================
    def _eng_format(self, num):
        if num == 0: return "0.000"
        sign = -1 if num < 0 else 1
        num = abs(num)
        
        exp = int(math.floor(math.log10(num) / 3.0) * 3)
        val = num / (10 ** exp)
        
        prefixes = {
            12: 'T', 9: 'G', 6: 'M', 3: 'k',
            0: '', -3: 'm', -6: 'µ', -9: 'n', -12: 'p', -15: 'f'
        }
        
        if exp in prefixes:
            return f"{sign * val:.3f} {prefixes[exp]}"
        else:
            return f"{sign * num:.3e}"

    def _setup_interactions(self):
        if hasattr(self, 'cid_press'):
            self.plot_canvas.mpl_disconnect(self.cid_press)
            self.plot_canvas.mpl_disconnect(self.cid_key)

        self.cid_press = self.plot_canvas.mpl_connect('button_press_event', self.on_mouse_click)
        self.cid_key = self.plot_canvas.mpl_connect('key_press_event', self.on_key_press)

    # --- FIX 2: Manually capture and kill draggable background tracking ---
    def _safe_remove(self, artist):
        if artist is None: return
        
        try:
            # First gracefully disable the physical drag capability 
            if hasattr(artist, 'set_draggable'): 
                artist.set_draggable(False)
            
            # Second, explicitly destroy the captured background loop memory 
            if hasattr(artist, '_drag_helper') and artist._drag_helper is not None:
                artist._drag_helper.disconnect()
            
            # Legacy matplotlib fallback
            if hasattr(artist, '_draggable') and artist._draggable is not None: 
                artist._draggable.disconnect()
        except Exception: 
            pass
            
        try: 
            artist.remove()
        except Exception: 
            pass

    def clear_markers(self, event=None):
        self.undo_stack = []
        
        if hasattr(self, 'markers'):
            for m in self.markers: self._safe_remove(m)
        self.markers = []
        
        for artist_list in [getattr(self, 'pt_A_artists', []), getattr(self, 'pt_B_artists', []),
                            getattr(self, 'pt_R_artists', []), getattr(self, 'pt_D_artists', [])]:
            for a in artist_list: self._safe_remove(a)
        
        self.pt_A_artists = []
        self.pt_B_artists = []
        self.pt_R_artists = []
        self.pt_D_artists = []
        self.pt_A_coords = None
        self.pt_B_coords = None
        self.pt_R_coords = None
        self.pt_D_coords = None
        
        if hasattr(self, 'delta_line_artist'):
            self._safe_remove(self.delta_line_artist)
            self.delta_line_artist = None
            
        if hasattr(self, 'delta_text_artist'):
            self._safe_remove(self.delta_text_artist)
            self.delta_text_artist = None
            
        if hasattr(self, 'delta_line_artist_RD'):
            self._safe_remove(self.delta_line_artist_RD)
            self.delta_line_artist_RD = None
            
        if hasattr(self, 'delta_text_artist_RD'):
            self._safe_remove(self.delta_text_artist_RD)
            self.delta_text_artist_RD = None
            
        if hasattr(self, 'plot_canvas'): 
            self.plot_canvas.draw_idle()

    def _create_annotated_marker(self, x, y, prefix=""):
        x_label = self.xlabel_var.get().split('(')[0].strip() 
        y_label = self.ylabel_var.get().split('(')[0].strip()
        
        x_str = self._eng_format(x)
        y_str = self._eng_format(y)
        
        text_parts = [
            f"{prefix}{x_label}: {x_str}",
            f"{y_label}: {y_str}"
        ]

        x_min, x_max = self.ax.get_xlim()
        y_min, y_max = self.ax.get_ylim()
        
        x_frac = (x - x_min) / (x_max - x_min) if self.ax.get_xscale() != 'log' else 0.5
        y_frac = (y - y_min) / (y_max - y_min) if self.ax.get_yscale() != 'log' else 0.5

        x_offset = -12 if x_frac > 0.85 else 12
        h_align = 'right' if x_frac > 0.85 else 'left'
        y_offset = -12 if y_frac > 0.85 else 12
        v_align = 'top' if y_frac > 0.85 else 'bottom'

        marker_text = self.ax.annotate(
            "\n".join(text_parts),
            xy=(x, y), xytext=(x_offset, y_offset), textcoords="offset points",
            ha=h_align, va=v_align,
            bbox=dict(facecolor='#FDFDFD', alpha=0.9, edgecolor='#B0B0B0', boxstyle='square,pad=0.4'),
            fontsize=10, zorder=6
        )
        
        # Save the physics tracking object directly onto the text artist so we can properly destroy it later
        drag_helper = None
        if hasattr(marker_text, 'set_draggable'): 
            marker_text.set_draggable(True)
        elif hasattr(marker_text, 'draggable'): 
            drag_helper = marker_text.draggable()
            
        marker_text._drag_helper = drag_helper
        
        return marker_text

    def on_key_press(self, event):
        # Prevent graph shortcuts from triggering if you are actively editing an input box
        if isinstance(self.focus_get(), (tk.Entry, ttk.Entry, ttk.Combobox)): 
            return 
            
        key = event.key.lower() if event.key else ''
        
        if key == 'c': self.clear_markers()
        elif key == 'p': self.generate_plot()
        elif key == 's': self.export_plot()
            
        if not event.inaxes: return
            
        if key == 'u':
            if hasattr(self, 'undo_stack') and self.undo_stack:
                action_type, artist1, artist2 = self.undo_stack.pop()
                
                self._safe_remove(artist1)
                self._safe_remove(artist2)
                
                if action_type == 'marker':
                    if artist2 in self.markers: self.markers.remove(artist2)
                    if artist1 in self.markers: self.markers.remove(artist1)
                elif action_type == 'A':
                    self.pt_A_artists = []
                    self.pt_A_coords = None
                    self._update_delta_line()
                elif action_type == 'B':
                    self.pt_B_artists = []
                    self.pt_B_coords = None
                    self._update_delta_line()
                elif action_type == 'R':
                    self.pt_R_artists = []
                    self.pt_R_coords = None
                    self._update_delta_line_RD()
                elif action_type == 'D':
                    self.pt_D_artists = []
                    self.pt_D_coords = None
                    self._update_delta_line_RD()
                    
                self.plot_canvas.draw_idle()
                
        elif key == 'a':
            self._set_delta_point('A', event.xdata, event.ydata)
            
        elif key == 'b':
            self._set_delta_point('B', event.xdata, event.ydata)
            
        elif key == 'r':
            self._set_delta_point_RD('R', event.xdata, event.ydata)
            
        elif key == 'd':
            self._set_delta_point_RD('D', event.xdata, event.ydata)

    def _set_delta_point(self, ptype, x, y):
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        artist_list = self.pt_A_artists if ptype == 'A' else self.pt_B_artists
        for a in artist_list:
            self._safe_remove(a)
            
        self.undo_stack = [item for item in self.undo_stack if item[0] != ptype]
            
        point_color = 'green' if ptype == 'A' else 'blue'
        
        m_pt = self.ax.plot(x, y, marker='^', color=point_color, markersize=8, zorder=6)[0]
        m_txt = self._create_annotated_marker(x, y, f"Point {ptype}\n")
        
        if ptype == 'A':
            self.pt_A_artists = [m_pt, m_txt]
            self.pt_A_coords = (x, y)
        else:
            self.pt_B_artists = [m_pt, m_txt]
            self.pt_B_coords = (x, y)
            
        self.undo_stack.append((ptype, m_pt, m_txt))
            
        self._update_delta_line()
        
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.plot_canvas.draw_idle()

    def _update_delta_line(self):
        if self.delta_line_artist:
            self._safe_remove(self.delta_line_artist)
        if self.delta_text_artist:
            self._safe_remove(self.delta_text_artist)
            
        if self.pt_A_coords and self.pt_B_coords:
            xA, yA = self.pt_A_coords
            xB, yB = self.pt_B_coords
            
            self.delta_line_artist = self.ax.plot([xA, xB], [yA, yB], color='black', linestyle='--', alpha=0.6, zorder=4)[0]
            
            mid_x = (xA + xB) / 2.0
            mid_y = (yA + yB) / 2.0
            
            dx_str = self._eng_format(abs(xA - xB))
            dy_str = self._eng_format(abs(yA - yB))
            
            text = f"Δx: {dx_str}\nΔy: {dy_str}"
            
            self.delta_text_artist = self.ax.annotate(
                text, xy=(mid_x, mid_y),
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFFBE6', edgecolor='gray', alpha=0.9),
                fontsize=10, zorder=5
            )
            
            drag_helper = None
            if hasattr(self.delta_text_artist, 'set_draggable'): 
                self.delta_text_artist.set_draggable(True)
            elif hasattr(self.delta_text_artist, 'draggable'): 
                drag_helper = self.delta_text_artist.draggable()
            
            self.delta_text_artist._drag_helper = drag_helper

    def _set_delta_point_RD(self, ptype, x, y):
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        artist_list = self.pt_R_artists if ptype == 'R' else self.pt_D_artists
        for a in artist_list:
            self._safe_remove(a)
            
        self.undo_stack = [item for item in self.undo_stack if item[0] != ptype]
            
        point_color = 'purple' if ptype == 'R' else 'orange'
        
        m_pt = self.ax.plot(x, y, marker='^', color=point_color, markersize=8, zorder=6)[0]
        m_txt = self._create_annotated_marker(x, y, f"Point {ptype}\n")
        
        if ptype == 'R':
            self.pt_R_artists = [m_pt, m_txt]
            self.pt_R_coords = (x, y)
        else:
            self.pt_D_artists = [m_pt, m_txt]
            self.pt_D_coords = (x, y)
            
        self.undo_stack.append((ptype, m_pt, m_txt))
            
        self._update_delta_line_RD()
        
        self.ax.set_xlim(xlim)
        self.ax.set_ylim(ylim)
        self.plot_canvas.draw_idle()

    def _update_delta_line_RD(self):
        if self.delta_line_artist_RD:
            self._safe_remove(self.delta_line_artist_RD)
        if self.delta_text_artist_RD:
            self._safe_remove(self.delta_text_artist_RD)
            
        if self.pt_R_coords and self.pt_D_coords:
            xR, yR = self.pt_R_coords
            xD, yD = self.pt_D_coords
            
            self.delta_line_artist_RD = self.ax.plot([xR, xD], [yR, yD], color='black', linestyle='--', alpha=0.6, zorder=4)[0]
            
            mid_x = (xR + xD) / 2.0
            mid_y = (yR + yD) / 2.0
            
            dx_str = self._eng_format(abs(xR - xD))
            dy_str = self._eng_format(abs(yR - yD))
            
            text = f"Δx: {dx_str}\nΔy: {dy_str}"
            
            self.delta_text_artist_RD = self.ax.annotate(
                text, xy=(mid_x, mid_y),
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#FFFBE6', edgecolor='gray', alpha=0.9),
                fontsize=10, zorder=5
            )
            
            drag_helper = None
            if hasattr(self.delta_text_artist_RD, 'set_draggable'): 
                self.delta_text_artist_RD.set_draggable(True)
            elif hasattr(self.delta_text_artist_RD, 'draggable'): 
                drag_helper = self.delta_text_artist_RD.draggable()
            
            self.delta_text_artist_RD._drag_helper = drag_helper

    def on_mouse_click(self, event):
        # Only claim focus for the canvas if you clicked away from a text entry box
        if not isinstance(self.focus_get(), (tk.Entry, ttk.Entry, ttk.Combobox)):
            self.plot_canvas.get_tk_widget().focus_set()
            
        if self.toolbar.mode != '': return 
        
        if event.button == 3 and event.inaxes:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            
            marker_text = self._create_annotated_marker(event.xdata, event.ydata)
            marker_point = self.ax.plot(event.xdata, event.ydata, marker='s', color='black', markersize=5, zorder=5)[0]

            self.markers.append(marker_text)
            self.markers.append(marker_point)
            
            self.undo_stack.append(('marker', marker_point, marker_text))
            
            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
            self.plot_canvas.draw_idle()

    # ==========================================
    # CORE PLOTTING ENGINES
    # ==========================================
    def _draw_eye(self, scale, yscale):
        try: data_rate = float(self.rate_var.get()) * 1e9
        except ValueError: 
            messagebox.showerror("Error", "Invalid Data Rate.")
            return False
            
        try: lw = float(self.linewidth_var.get())
        except ValueError: lw = 0.5
            
        UI = 1.0 / data_rate
        num_uis = 2  
        global_min, global_max = float('inf'), float('-inf')
        theme = self.theme_var.get()
        plotted_anything = False

        for i, (x_arr, y_arr) in enumerate(self.raw_data):
            if len(x_arr) < 2: continue
            
            time_shifted = x_arr - x_arr[0]
            num_segments = int(time_shifted[-1] / UI) - num_uis
            
            if num_segments < 1 or num_segments > 50000: continue
                
            slice_indices = []
            for j in range(num_segments):
                start = np.searchsorted(time_shifted, j * UI)
                end = np.searchsorted(time_shifted, (j + num_uis) * UI)
                if end < len(time_shifted): slice_indices.append((start, end, j * UI))
                    
            y_scaled = y_arr * yscale
            global_min = min(global_min, np.min(y_scaled))
            global_max = max(global_max, np.max(y_scaled))
            
            segments = []
            for start, end, t_offset in slice_indices:
                t_folded = (time_shifted[start:end] - t_offset) * scale
                segments.append(np.column_stack([t_folded, y_scaled[start:end]]))
                
            if theme == "Modern Color (MATLAB)": color = PALETTE_COLOR[i % len(PALETTE_COLOR)]
            elif theme == "Classic Grayscale": color = PALETTE_GRAY[i % len(PALETTE_GRAY)]
            elif theme == "Custom (Per Trace)": color = self.trace_vars[i]['color'].get()
                
            alpha_val = 0.5 if len(segments) < 100 else 0.15
            lc = LineCollection(segments, colors=color, alpha=alpha_val, linewidths=lw, antialiased=False)
            self.ax.add_collection(lc)
            plotted_anything = True
            
        if not plotted_anything:
            messagebox.showwarning("Eye Diagram Failed", "Could not generate eye diagram.\n\nEnsure you loaded Transient data (Time vs Voltage), not DC sweep data.")
            return False
            
        self.ax.set_xlim(0, num_uis * UI * scale)
        pad = (global_max - global_min) * 0.1
        self.ax.set_ylim(global_min - pad, global_max + pad)
        return True

    def _draw_standard(self, scale, yscale):
        theme = self.theme_var.get()
        all_solid = self.linestyle_var.get() == "All Solid"
        
        try: lw = float(self.linewidth_var.get())
        except ValueError: lw = 3.0 
            
        styles = ['-'] if all_solid else ['-', '--', '-.', ':']
        
        global_x_min, global_x_max = float('inf'), float('-inf')
        
        for i, (x_array, y_array) in enumerate(self.raw_data):
            if len(x_array) == 0: continue
                
            style = styles[i % len(styles)]
            if theme == "Modern Color (MATLAB)":
                color = PALETTE_COLOR[i % len(PALETTE_COLOR)]
                label_name = self.trace_vars[i]['name'].get() if i < len(self.trace_vars) else f"Trace {i+1}"
            elif theme == "Classic Grayscale":
                color = PALETTE_GRAY[i % len(PALETTE_GRAY)]
                label_name = self.trace_vars[i]['name'].get() if i < len(self.trace_vars) else f"Trace {i+1}"
            elif theme == "Custom (Per Trace)":
                color = self.trace_vars[i]['color'].get() if i < len(self.trace_vars) else 'black'
                label_name = self.trace_vars[i]['name'].get() if i < len(self.trace_vars) else f"Trace {i+1}"
            
            x_scaled = x_array * scale
            y_scaled = y_array * yscale
            
            global_x_min = min(global_x_min, np.min(x_scaled))
            global_x_max = max(global_x_max, np.max(x_scaled))
            
            marker_style = 'o' if len(x_scaled) == 1 else None
            self.ax.plot(x_scaled, y_scaled, linestyle=style, color=color, linewidth=lw, label=label_name, marker=marker_style, markersize=8)
            
        if len(self.raw_data) > 0:
            # Dynamically calculate columns to prevent the box from getting too tall
            num_traces = len(self.raw_data)
            col_count = 1 if num_traces <= 4 else (2 if num_traces <= 8 else 3)

            leg = self.ax.legend(
                loc='best', 
                frameon=True, 
                edgecolor='black', 
                fontsize=9,              
                ncol=col_count,          
                labelspacing=0.4,        
                handlelength=2.0,        
                handletextpad=0.6,       
                borderpad=0.5,           
                borderaxespad=1.0        
            )
            
            if leg:
                leg.set_draggable(True)
                
                # FIX: Smart-Snap algorithm to survive 10x5 Export Resizing without touching the export function
                def _snap_legend_to_corner(event):
                    if event.button == 1 and hasattr(self, 'ax') and leg:
                        try:
                            # 1. Get the center of the dragged legend in proportional Axes coordinates (0.0 to 1.0)
                            bbox = leg.get_window_extent().transformed(self.ax.transAxes.inverted())
                            cx, cy = (bbox.x0 + bbox.x1) / 2, (bbox.y0 + bbox.y1) / 2
                            
                            # 2. Determine the nearest logical region (Quadrant)
                            v = 'upper' if cy > 0.6 else ('lower' if cy < 0.4 else 'center')
                            h = 'right' if cx > 0.6 else ('left' if cx < 0.4 else 'center')
                            
                            new_loc = 'center' if v == 'center' and h == 'center' else \
                                      f"center {h}" if v == 'center' else \
                                      f"{v} center" if h == 'center' else f"{v} {h}"
                            
                            # 3. Strip the rigid pixel lock from the drag, and apply the dynamic quadrant lock
                            leg._loc = leg.codes.get(new_loc, 0)
                            try: leg.set_bbox_to_anchor(None)
                            except: pass
                            leg._bbox_to_anchor = None
                            
                            self.plot_canvas.draw_idle()
                        except Exception:
                            pass
                            
                # Safely register the release hook
                if hasattr(self, '_leg_snap_cid'):
                    self.plot_canvas.mpl_disconnect(self._leg_snap_cid)
                self._leg_snap_cid = self.plot_canvas.mpl_connect('button_release_event', _snap_legend_to_corner)
            
            if global_x_min != float('inf') and global_x_max != float('-inf'):
                self.ax.set_xlim(global_x_min, global_x_max)
            
        if self.logx_var.get():
            self.ax.set_xscale('log')

    def export_plot(self, event=None):
        if not self.file_loaded: return
        save_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")])
        if save_path:
            current_size = self.fig.get_size_inches()
            self.fig.set_size_inches(10, 5)
            self.fig.tight_layout()
            self.fig.savefig(save_path, dpi=300, bbox_inches='tight', pad_inches=0.15)
            self.fig.set_size_inches(current_size)
            self.fig.tight_layout()
            messagebox.showinfo("Saved", f"High-resolution plot saved to:\n{save_path}")

if __name__ == '__main__':
    app = UniversalIEEEPlotterApp()
    app.mainloop()