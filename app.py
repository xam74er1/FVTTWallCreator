import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk  # Import ttk for themed widgets
from tkinter import filedialog, messagebox
from tkinter.ttk import Style # Import Style for theme configuration
from PIL import Image, ImageTk, Image as PILImage # Use alias
import json
import re # For input validation
import os # Added for default filename

# >>> Placeholder for send_token - replace with your actual import <<<
def send_token(cookie_id, image_path, data, map_name, x_scale=1.0, y_scale=1.0):
    print("--- MOCK send_token ---")
    print(f"Cookie: {cookie_id}")
    print(f"Image Path: {image_path}")
    print(f"Map Name: {map_name}")
    print(f"X Scale: {x_scale}")
    print(f"Y Scale: {y_scale}")
    print(f"Data Keys: {list(data.keys())}")
    if 'lines' in data:
        print(f"  Num Lines: {len(data['lines'])}")
    if 'polygons' in data:
        print(f"  Num Polygons: {len(data['polygons'])}")
    print("-----------------------")
    # In real usage, this would contain the actual HTTP request logic
    pass
# --- End Placeholder ---


# Import shapely (optional)
try:
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    print("Warning: Shapely library not found. Polygon merging will be disabled.")

# Import KDTree (optional)
try:
    from scipy.spatial import KDTree
    KDTREE_AVAILABLE = True
except ImportError:
    KDTREE_AVAILABLE = False
    print("Warning: scipy.spatial.KDTree not found. Line merging might be slower.")


# --- Dark Theme Colors ---
COLOR_PRIMARY_BG = "#2E2E2E"
COLOR_SECONDARY_BG = "#3C3C3C"
COLOR_TEXT = "#E0E0E0"
COLOR_ACCENT = "#007ACC"      # Blue accent
COLOR_ACCENT_DARKER = "#005FA3" # Darker blue for hover/press
COLOR_ACCENT_DARKEST = "#004C82" # Even darker blue
COLOR_BUTTON_TEXT = "#FFFFFF"
COLOR_CANVAS_BG = "#4A4A4A"
COLOR_POLYGON = "#FF6B6B"    # Reddish color for polygons
COLOR_LINE = "#4ECDC4"       # Teal color for lines
COLOR_DISABLED_TEXT = "#888888" # Color for disabled text/widgets
COLOR_ENTRY_BG = "#555555" # Slightly different background for Entry
COLOR_ENTRY_TEXT = "#F0F0F0"
COLOR_ENTRY_BORDER = "#777777" # Border for Entry widget focus

class WallLineDetectorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Modern Battlemap Wall & Line Detector")
        self.master.configure(bg=COLOR_PRIMARY_BG)

        # --- Configure Master Grid ---
        self.master.rowconfigure(0, weight=1) # Main content row expands vertically
        self.master.columnconfigure(0, weight=0) # Controls Panel (fixed width)
        self.master.columnconfigure(1, weight=1) # Processed Image Canvas (expands)
        self.master.columnconfigure(2, weight=1) # Original + Overlay Canvas (expands)
        # --- Change: Export Panel column weight 0 ensures minimum width ---
        self.master.columnconfigure(3, weight=0) # Export Panel (fixed minimum width)

        # Image Data
        self.img = None             # Original loaded (and resized) image (OpenCV BGR)
        self.processed_img = None   # Original image with overlays (OpenCV BGR)
        self.intermediate_processed_img = None # Intermediate image for detection (e.g., edges, grayscale)
        self.tk_img = None          # Tkinter PhotoImage for the main canvas
        self.tk_processed_img = None # Tkinter PhotoImage for the processed canvas
        self.filepath = None
        self.original_image_dims = (0, 0) # Store original dimensions before resize

        # Detected Elements
        self.contours = []
        self.lines = []

        # OpenCV Tools
        self.lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)

        # Styling
        self.style = Style(self.master)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            print("Clam theme not available, using default.")
            self.style.theme_use('default')

        # --- Configure Style Elements ---
        default_font = ('Segoe UI', 9)
        self.style.configure('.',
                             background=COLOR_PRIMARY_BG,
                             foreground=COLOR_TEXT,
                             fieldbackground=COLOR_SECONDARY_BG,
                             selectbackground=COLOR_ACCENT,
                             selectforeground=COLOR_BUTTON_TEXT,
                             font=default_font)

        self.style.configure('TFrame', background=COLOR_PRIMARY_BG)
        self.style.configure('TLabel', background=COLOR_PRIMARY_BG, foreground=COLOR_TEXT, padding=(5, 3))
        self.style.configure('Value.TLabel', background=COLOR_PRIMARY_BG, foreground=COLOR_TEXT, padding=(2, 3), font=('Segoe UI', 8)) # Smaller label for value display
        self.style.configure('Bold.TLabel', font=('Segoe UI', 9, 'bold'))

        # Button Styling
        self.style.configure('TButton', background=COLOR_ACCENT, foreground=COLOR_BUTTON_TEXT, padding=(10, 5), relief=tk.FLAT, borderwidth=0, anchor=tk.CENTER) # Reduced padding slightly
        self.style.map('TButton',
                       background=[('pressed', COLOR_ACCENT_DARKEST), ('active', COLOR_ACCENT_DARKER), ('disabled', COLOR_SECONDARY_BG)],
                       foreground=[('disabled', COLOR_DISABLED_TEXT)],
                       relief=[('pressed', tk.FLAT)], borderwidth=[('pressed', 0), ('!pressed', 0)])

        # Checkbutton Styling
        self.style.configure('TCheckbutton', background=COLOR_PRIMARY_BG, foreground=COLOR_TEXT, indicatorrelief=tk.FLAT, indicatormargin=5, padding=(5, 3))
        self.style.map('TCheckbutton',
                       background=[('active', COLOR_SECONDARY_BG)],
                       indicatorbackground=[('selected', COLOR_ACCENT), ('active', COLOR_SECONDARY_BG)],
                       indicatorforeground=[('selected', COLOR_BUTTON_TEXT)])

        # Scale Styling
        self.style.configure('TScale', background=COLOR_PRIMARY_BG)
        self.style.configure('Horizontal.TScale', troughcolor=COLOR_SECONDARY_BG, sliderlength=25, sliderrelief=tk.FLAT, background=COLOR_ACCENT)
        self.style.map('Horizontal.TScale',
                        background=[('active', COLOR_ACCENT_DARKER), ('disabled', COLOR_SECONDARY_BG)],
                        troughcolor=[('disabled', COLOR_PRIMARY_BG)])

        # Entry Styling
        self.style.configure('TEntry',
                             fieldbackground=COLOR_ENTRY_BG,
                             foreground=COLOR_ENTRY_TEXT,
                             insertcolor=COLOR_TEXT,
                             borderwidth=1,
                             relief=tk.FLAT)
        self.style.map('TEntry',
                       bordercolor=[('focus', COLOR_ACCENT)],
                       fieldbackground=[('disabled', COLOR_SECONDARY_BG)],
                       foreground=[('disabled', COLOR_DISABLED_TEXT)])

        # Separator
        self.style.configure('TSeparator', background=COLOR_SECONDARY_BG)
        # --- End Style Config ---


        self.slider_widgets = {} # Store slider widgets

        # Debounce Timer
        self._debounce_timer = None

        # Canvas Widgets (declared before create_widgets for potential early access)
        self.processed_canvas = None
        self.canvas = None

        # Create UI
        self.create_widgets()

    def create_widgets(self):
        # --- Control Panel (Left - Column 0) ---
        control_frame = ttk.Frame(self.master, padding="15 15 15 15")
        control_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        # Control frame still needs its own column config for its sliders
        control_frame.columnconfigure(1, weight=1)  # Scale column expands
        control_frame.columnconfigure(2, weight=0, minsize=50)  # Fixed size for entry

        row_idx = 0

        # --- Modified add_separator ---
        # Now takes optional cols parameter, defaulting to 3 for control_frame
        def add_separator(parent_frame, current_row_idx, cols=3):
            sep = ttk.Separator(parent_frame, orient=tk.HORIZONTAL)
            sep.grid(row=current_row_idx, column=0, columnspan=cols, sticky="ew", pady=(15, 10))
            return current_row_idx + 1  # Return the next row index

        # --- File Operations ---
        ttk.Label(control_frame, text="File", style='Bold.TLabel').grid(row=row_idx, column=0, columnspan=3, sticky="w",
                                                                        pady=(0, 5))
        row_idx += 1
        self.load_button = ttk.Button(control_frame, text="Load Image", command=self.load_image)
        self.load_button.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=3, sticky="ew")
        row_idx += 1
        self.save_button = ttk.Button(control_frame, text="Save Overlay Image", command=self.save_display_image)
        self.save_button.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=3, sticky="ew")
        row_idx += 1

        row_idx = add_separator(control_frame, row_idx)  # Use helper

        # --- Display Options & Counts ---
        ttk.Label(control_frame, text="Display", style='Bold.TLabel').grid(row=row_idx, column=0, columnspan=3,
                                                                           sticky="w", pady=(0, 5))
        row_idx += 1
        self.show_polygons_var = tk.BooleanVar(value=True)
        self.show_lines_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame, text="Show Polygons", variable=self.show_polygons_var,
                        command=self.update_display).grid(row=row_idx, column=0, columnspan=3, sticky="w", padx=5,
                                                          pady=1)
        row_idx += 1
        ttk.Checkbutton(control_frame, text="Show Lines", variable=self.show_lines_var,
                        command=self.update_display).grid(
            row=row_idx, column=0, columnspan=3, sticky="w", padx=5, pady=1)
        row_idx += 1
        self.poly_count_label = ttk.Label(control_frame, text="Polygons: 0")
        self.poly_count_label.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=(5, 0), sticky="w")
        row_idx += 1
        self.line_count_label = ttk.Label(control_frame, text="Lines: 0")
        self.line_count_label.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=(0, 5), sticky="w")
        row_idx += 1

        row_idx = add_separator(control_frame, row_idx)  # Use helper

        # --- Detection Parameters ---
        ttk.Label(control_frame, text="Detection Params", style='Bold.TLabel').grid(row=row_idx, column=0, columnspan=3,
                                                                                    sticky="w", pady=(0, 5))
        row_idx += 1

        # --- Modified: add_slider_control uses parent's row_idx management ---
        def add_slider_control(name, label_text, from_val, to_val, default_val, is_epsilon=False,
                               parent_frame=control_frame, start_row_idx=0):
            current_row = start_row_idx  # Use passed row index
            ttk.Label(parent_frame, text=label_text).grid(row=current_row, column=0, sticky="w", padx=(5, 10))
            scale = ttk.Scale(parent_frame, from_=from_val, to=to_val, orient=tk.HORIZONTAL)
            scale.set(default_val)
            scale.grid(row=current_row, column=1, sticky="ew", padx=5, pady=1)

            entry_frame = ttk.Frame(parent_frame)
            entry_frame.grid(row=current_row, column=2, sticky="ew", padx=(5, 0))
            entry_frame.columnconfigure(0, weight=1)

            entry_var = tk.StringVar()
            entry = ttk.Entry(entry_frame, textvariable=entry_var, width=6, justify='right')
            entry.grid(row=0, column=0, sticky='ew')

            suffix_label = None
            if is_epsilon:
                suffix_label = ttk.Label(entry_frame, text="%", style='Value.TLabel')
                suffix_label.grid(row=0, column=1, sticky='w', padx=(1, 0))

            # Store widgets (use self.slider_widgets directly)
            self.slider_widgets[name] = {'scale': scale, 'entry': entry, 'var': entry_var, 'from': from_val,
                                         'to': to_val, 'is_epsilon': is_epsilon, 'suffix_label': suffix_label}
            self.update_value_display(name)  # Initialize display
            scale.config(command=lambda val, n=name: self.handle_slider_change(val, n))
            entry.bind("<Return>", lambda event, n=name: self.handle_entry_change(event, n))
            entry.bind("<FocusOut>", lambda event, n=name: self.handle_entry_change(event, n))
            entry.bind("<KP_Enter>", lambda event, n=name: self.handle_entry_change(event, n))
            return current_row + 1  # Return the next available row index

        # Add detection sliders to control_frame
        row_idx = add_slider_control('canny1', "Canny Thresh 1", 0, 500, 50, parent_frame=control_frame,
                                     start_row_idx=row_idx)
        row_idx = add_slider_control('canny2', "Canny Thresh 2", 0, 500, 150, parent_frame=control_frame,
                                     start_row_idx=row_idx)
        row_idx = add_slider_control('epsilon', "Approx. Eps (%)", 0, 1000, 30, is_epsilon=True,
                                     parent_frame=control_frame, start_row_idx=row_idx)  # Range 0-100.0%
        row_idx = add_slider_control('blur', "Blur Kernel", 1, 10, 2, parent_frame=control_frame, start_row_idx=row_idx)
        row_idx = add_slider_control('morph', "Morph Kernel", 0, 5, 0, parent_frame=control_frame,
                                     start_row_idx=row_idx)
        row_idx = add_slider_control('area', "Min Area", 0, 2000, 100, parent_frame=control_frame,
                                     start_row_idx=row_idx)

        row_idx = add_separator(control_frame, row_idx)  # Use helper

        # --- Merge Options ---
        ttk.Label(control_frame, text="Merging", style='Bold.TLabel').grid(row=row_idx, column=0, columnspan=3,
                                                                           sticky="w", pady=(0, 5))
        row_idx += 1
        self.merge_lines_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame, text="Merge Close Lines", variable=self.merge_lines_var,
                        command=self.process_image_debounced).grid(row=row_idx, column=0, columnspan=3, sticky="w",
                                                                   padx=5, pady=1)
        row_idx += 1
        row_idx = add_slider_control('line_thresh', "Line Thresh", 1, 100, 20, parent_frame=control_frame,
                                     start_row_idx=row_idx)

        self.merge_polygons_var = tk.BooleanVar(value=False)
        self.poly_merge_check = ttk.Checkbutton(control_frame, text="Merge Close Polygons",
                                                variable=self.merge_polygons_var,
                                                command=self.process_image_debounced)
        self.poly_merge_check.grid(row=row_idx, column=0, columnspan=3, sticky="w", padx=5, pady=1)
        # Place disabled label near checkbox if needed
        if not SHAPELY_AVAILABLE:
            ttk.Label(control_frame, text="(Requires Shapely)", font="-size 8", foreground=COLOR_DISABLED_TEXT).grid(
                row=row_idx, column=1, columnspan=2, sticky='e', padx=5)
        row_idx += 1
        row_idx = add_slider_control('poly_thresh', "Poly Thresh", 1, 100, 20, parent_frame=control_frame,
                                     start_row_idx=row_idx)

        if not SHAPELY_AVAILABLE:
            self.merge_polygons_var.set(False)
            self.poly_merge_check.config(state=tk.DISABLED)
            widgets = self.slider_widgets.get('poly_thresh')
            if widgets:
                widgets['scale'].config(state=tk.DISABLED)
                widgets['entry'].config(state=tk.DISABLED)

        row_idx = add_separator(control_frame, row_idx)  # Use helper

        # --- JSON Export Buttons (in Control Panel) ---
        ttk.Label(control_frame, text="File Export", style='Bold.TLabel').grid(row=row_idx, column=0, columnspan=3,
                                                                               sticky="w", pady=(0, 5))
        row_idx += 1
        self.export_lines_button = ttk.Button(control_frame, text="Export Lines (JSON)",
                                              command=lambda: self.export_json(save_polygons=False, save_lines=True))
        self.export_lines_button.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=3, sticky="ew")
        row_idx += 1
        self.export_polygons_button = ttk.Button(control_frame, text="Export Polygons (JSON)",
                                                 command=lambda: self.export_json(save_polygons=True, save_lines=False))
        self.export_polygons_button.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=3, sticky="ew")
        row_idx += 1

        control_frame.rowconfigure(row_idx, weight=1)  # Push controls up

        # --- Processed Image Canvas Frame (Center-Left - Column 1) ---
        processed_canvas_frame = ttk.Frame(self.master)
        processed_canvas_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 5), pady=10)
        processed_canvas_frame.rowconfigure(1, weight=1)  # Canvas row expands
        processed_canvas_frame.columnconfigure(0, weight=1)  # Canvas col expands
        ttk.Label(processed_canvas_frame, text="Processing View (Edges)", anchor=tk.CENTER).grid(row=0, column=0,
                                                                                                 sticky="ew",
                                                                                                 pady=(0, 5))
        self.processed_canvas = tk.Canvas(processed_canvas_frame, width=400, height=400, bg=COLOR_CANVAS_BG,
                                          highlightthickness=0)
        self.processed_canvas.grid(row=1, column=0, sticky="nsew")

        # --- Original + Overlays Canvas Frame (Center-Right - Column 2) ---
        original_canvas_frame = ttk.Frame(self.master)
        original_canvas_frame.grid(row=0, column=2, sticky="nsew", padx=(5, 5), pady=10)
        original_canvas_frame.rowconfigure(1, weight=1)  # Canvas row expands
        original_canvas_frame.columnconfigure(0, weight=1)  # Canvas col expands
        ttk.Label(original_canvas_frame, text="Original + Overlays", anchor=tk.CENTER).grid(row=0, column=0,
                                                                                            sticky="ew", pady=(0, 5))
        self.canvas = tk.Canvas(original_canvas_frame, width=400, height=400, bg=COLOR_CANVAS_BG, highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew")

        # --- Export/Foundry Panel (Right - Column 3) ---
        export_panel = ttk.Frame(self.master, padding="15 15 15 15")
        # --- Change: Use "ns" sticky to prevent horizontal stretching beyond content needs ---
        export_panel.grid(row=0, column=3, sticky="ns", padx=(5, 10), pady=10)

        # --- Change: Configure internal columns to accommodate sliders ---
        export_panel.columnconfigure(0, weight=0)  # Label column (fixed width)
        export_panel.columnconfigure(1, weight=1)  # Scale column (expands to fill available slider space)
        export_panel.columnconfigure(2, weight=0, minsize=60)  # Entry column (fixed width, slightly wider for %)

        row_idx_export = 0

        # --- Use the modified add_separator, specifying 3 columns for this panel ---
        def add_export_separator(current_row_idx):
            return add_separator(export_panel, current_row_idx, cols=3)

        # --- Change: Make title span all 3 internal columns ---
        ttk.Label(export_panel, text="Foundry Export", style='Bold.TLabel').grid(row=row_idx_export, column=0,
                                                                                 columnspan=3, sticky="ew", pady=(0, 5))
        row_idx_export += 1

        # --- Change: Make labels/entries span all 3 columns ---
        ttk.Label(export_panel, text="Cookie ID").grid(row=row_idx_export, column=0, columnspan=3, sticky="w",
                                                       pady=(5, 0))
        row_idx_export += 1
        self.cookie_id_entry = ttk.Entry(export_panel)
        self.cookie_id_entry.grid(row=row_idx_export, column=0, columnspan=3, padx=0, pady=(0, 5), sticky="ew")
        row_idx_export += 1

        ttk.Label(export_panel, text="Map Name").grid(row=row_idx_export, column=0, columnspan=3, sticky="w",
                                                      pady=(5, 0))
        row_idx_export += 1
        self.map_name_entry = ttk.Entry(export_panel)
        self.map_name_entry.grid(row=row_idx_export, column=0, columnspan=3, padx=0, pady=(0, 10), sticky="ew")
        row_idx_export += 1

        row_idx_export = add_export_separator(row_idx_export)  # Use helper

        # --- Change: Add Scale Factor Sliders BACK to export_panel ---
        # Use the modified add_slider_control, passing the export_panel and its row index
        row_idx_export = add_slider_control('x_scale_factor', "X Scale Factor (%)", 1, 5000, 1000, is_epsilon=True,
                                            parent_frame=export_panel,
                                            start_row_idx=row_idx_export)  # 0.1% to 500.0%, default 100.0%
        row_idx_export = add_slider_control('y_scale_factor', "Y Scale Factor (%)", 1, 5000, 1000, is_epsilon=True,
                                            parent_frame=export_panel,
                                            start_row_idx=row_idx_export)  # 0.1% to 500.0%, default 100.0%
        # --- End Scale Factor Sliders ---

        row_idx_export = add_export_separator(row_idx_export)  # Use helper

        # --- Change: Make Buttons span all 3 columns and use sticky="ew" ---
        self.create_wall_from_line_button = ttk.Button(export_panel, text="Send Walls (Lines)",
                                                       command=self.create_wall_from_line)
        self.create_wall_from_line_button.grid(row=row_idx_export, column=0, columnspan=3, padx=0, pady=3, sticky="ew")
        row_idx_export += 1

        self.create_wall_from_polygon_button = ttk.Button(export_panel, text="Send Walls (Polygons)",
                                                          command=self.create_wall_from_polygon)
        self.create_wall_from_polygon_button.grid(row=row_idx_export, column=0, columnspan=3, padx=0, pady=3,
                                                  sticky="ew")
        row_idx_export += 1

        # Add empty row at bottom to push export controls up if needed (weight 1)
        export_panel.rowconfigure(row_idx_export, weight=1)


    # --- Update and Handling Logic ---

    def handle_slider_change(self, slider_value, widget_name):
        """Called when a slider is moved."""
        self.update_value_display(widget_name)
        self.process_image_debounced()

    def handle_entry_change(self, event, widget_name):
        """Called when Enter/FocusOut occurs on an Entry."""
        widgets = self.slider_widgets.get(widget_name)
        if not widgets: return

        scale = widgets['scale']
        entry = widgets['entry']
        entry_var = widgets['var']
        from_val = widgets['from']
        to_val = widgets['to']
        is_epsilon = widgets['is_epsilon']

        current_entry_text = entry_var.get().replace('%', '') # Strip % if present

        try:
            numeric_value = float(current_entry_text)

            # Handle percentage sliders correctly (input is direct percentage)
            if is_epsilon:
                # Clamp the direct percentage input first
                clamped_percent = max(from_val / 10.0, min(to_val / 10.0, numeric_value))
                # Convert clamped percentage back to slider scale value
                target_scale_val = clamped_percent * 10.0
            else:
                target_scale_val = numeric_value

            # Special handling for Blur/Morph kernel sliders (must result in odd kernel size)
            if widget_name == 'blur' or widget_name == 'morph':
                 # Ensure slider step corresponds to kernel step (0, 1->3, 2->5, etc.)
                 target_scale_val = round(numeric_value) # Just round the input factor

            # Clamp scale value to slider bounds AFTER conversion
            clamped_scale_val = max(from_val, min(to_val, target_scale_val))
            # final_scale_val = round(clamped_scale_val) # Round to nearest integer for most
            # Keep precision for epsilon slider
            final_scale_val = round(clamped_scale_val, 1) if is_epsilon else round(clamped_scale_val)

            scale.set(final_scale_val)
            self.update_value_display(widget_name) # Update entry display after setting scale

        except ValueError:
            print(f"Invalid input: '{current_entry_text}'. Reverting.")
            self.update_value_display(widget_name) # Revert entry to match slider

    def update_value_display(self, widget_name):
        """Updates the Entry text based on the current Slider value."""
        widgets = self.slider_widgets.get(widget_name)
        if not widgets: return

        scale = widgets['scale']
        entry_var = widgets['var']
        is_epsilon = widgets['is_epsilon']
        suffix_label = widgets.get('suffix_label') # Get the suffix label

        try:
            scale_value = float(scale.get()) # Use float for precision
        except (ValueError, tk.TclError):
            scale_value = widgets['from'] # Default to min if error
            scale.set(scale_value)

        # Display as percentage if needed, otherwise integer
        if is_epsilon:
            display_value = f"{scale_value / 10.0:.1f}" # Show one decimal place for percentage
            if suffix_label: suffix_label.config(text="%") # Ensure label shows %
        else:
            display_value = f"{round(scale_value):d}" # Display as integer
            if suffix_label: suffix_label.config(text="") # Hide label if not %

        entry_var.set(display_value)


    # --- Debounce mechanism ---
    def process_image_debounced(self, event=None):
        if self._debounce_timer is not None:
            self.master.after_cancel(self._debounce_timer)
        self._debounce_timer = self.master.after(250, self.process_image) # 250ms delay

    # --- Core Processing ---
    def process_image(self, event=None):
        self._debounce_timer = None
        if self.img is None: return

        # Retrieve parameters
        try:
            thresh1 = int(round(float(self.slider_widgets['canny1']['scale'].get())))
            thresh2 = int(round(float(self.slider_widgets['canny2']['scale'].get())))
            # Epsilon value is percentage * 10 on slider, so divide by 1000 (10 * 100)
            epsilon_scale_val = float(self.slider_widgets['epsilon']['scale'].get())
            epsilon_percent = epsilon_scale_val / 1000.0 # Convert slider val (0-1000) to percentage (0-1.0)

            blur_factor = int(round(float(self.slider_widgets['blur']['scale'].get())))
            kernel_size = max(1, 2 * blur_factor + 1) # Ensure odd kernel size > 0

            morph_factor = int(round(float(self.slider_widgets['morph']['scale'].get())))
            morph_size = 2 * morph_factor + 1 if morph_factor > 0 else 0 # Morph size (0 if factor is 0)

            min_area = int(round(float(self.slider_widgets['area']['scale'].get())))

            do_merge_lines = self.merge_lines_var.get()
            line_merge_thresh = round(float(self.slider_widgets['line_thresh']['scale'].get()))

            do_merge_polygons = self.merge_polygons_var.get() and SHAPELY_AVAILABLE
            poly_merge_thresh = 0
            if SHAPELY_AVAILABLE: # Avoid error if disabled
                 poly_merge_thresh = round(float(self.slider_widgets['poly_thresh']['scale'].get()))

        except (ValueError, tk.TclError, KeyError) as e:
            print(f"Warning: Error getting slider value during processing: {e}")
            # Attempt to update displays even if params failed, might show old results
            self.update_display()
            if self.intermediate_processed_img is not None:
                self.display_intermediate_on_canvas(self.intermediate_processed_img)
            return

        # --- Image Processing Core ---
        try:
            gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)
            edges = cv2.Canny(blurred, thresh1, thresh2)

            edges_for_poly = edges.copy()
            if morph_factor > 0 and morph_size > 0:
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (morph_size, morph_size))
                # Use closing (dilate then erode) or dilation? Let's stick with dilation for now.
                edges_for_poly = cv2.dilate(edges_for_poly, kernel, iterations=1)
                # edges_for_poly = cv2.morphologyEx(edges_for_poly, cv2.MORPH_CLOSE, kernel) # Alternative: Closing

            # *** Store the intermediate image for the processed view ***
            self.intermediate_processed_img = edges_for_poly.copy()

            # Polygon detection (using edges_for_poly)
            contours_raw, _ = cv2.findContours(edges_for_poly, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            poly_list = []
            for cnt in contours_raw:
                if len(cnt) < 3: continue # Need at least 3 points for a polygon
                perimeter = cv2.arcLength(cnt, True)
                if perimeter <= 0: continue # Avoid division by zero for epsilon calc

                # Calculate epsilon based on perimeter
                epsilon = epsilon_percent * perimeter
                approx = cv2.approxPolyDP(cnt, epsilon, True) # True for closed polygons

                # Check area and validity AFTER approximation
                if len(approx) >= 3 and cv2.contourArea(approx) > min_area:
                     poly_list.append(approx)

            if do_merge_polygons:
                poly_list = self.merge_polygons(poly_list, poly_merge_thresh)
            self.contours = poly_list

            # Line detection (using the original 'edges' before morphology for potentially cleaner lines)
            # Adjust LSD parameters if needed (e.g., _scale, _sigma_scale) - using defaults here
            detected_lines = self.lsd.detect(edges) # Use 'edges' not 'edges_for_poly'
            line_list = []
            if detected_lines is not None and detected_lines[0] is not None:
                min_line_length_sq = 5**2 # Filter very short lines (e.g., less than 5 pixels)
                for dline in detected_lines[0]:
                    x1, y1, x2, y2 = map(int, dline[0])
                    if (x2-x1)**2 + (y2-y1)**2 >= min_line_length_sq:
                        line_list.append((x1, y1, x2, y2))

            if do_merge_lines:
                line_list = self.merge_lines(line_list, line_merge_thresh)
            self.lines = line_list

            # Update counts
            self.poly_count_label.config(text=f"Polygons: {len(self.contours)}")
            self.line_count_label.config(text=f"Lines: {len(self.lines)}")

            # Update BOTH displays
            self.update_display() # Updates the original + overlays canvas
            self.display_intermediate_on_canvas(self.intermediate_processed_img) # Update the processed view canvas

        except Exception as e:
            messagebox.showerror("Processing Error", f"An error occurred during image processing:\n{e}", parent=self.master)
            print(f"Processing error details: {e}") # Log detailed error


    # --- Methods (Load, Clear, Resize, Merge, Display, Save, Export) ---

    def load_image(self):
        self.filepath = filedialog.askopenfilename(parent=self.master, filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if not self.filepath: return
        try:
            img_bgr = cv2.imread(self.filepath)
            if img_bgr is None: raise ValueError("File could not be read by OpenCV.")

            # Store original dimensions BEFORE resizing
            self.original_image_dims = (img_bgr.shape[1], img_bgr.shape[0]) # width, height

            # Determine max size based on available screen space (leaving room for controls)
            self.master.update_idletasks() # Ensure window sizes are calculated
            controls_width = self.master.winfo_reqwidth() * 0.3 # Estimate width (adjust as needed)
            export_width = self.master.winfo_reqwidth() * 0.15 # Estimate width
            available_width = self.master.winfo_width() - controls_width - export_width - 60 # Subtract padding/margins
            canvas_max_width = available_width / 2 # Divide remaining space by 2 canvases
            canvas_max_height = self.master.winfo_height() * 0.9 # Use most of the height

            if canvas_max_width <= 0 or canvas_max_height <= 0:
                 # Fallback if calculated sizes are invalid (e.g., window too small initially)
                 canvas_max_width = 400
                 canvas_max_height = 400
                 print("Warning: Could not accurately determine canvas size, using default 400x400.")

            self.img = self.resize_image(img_bgr, int(canvas_max_width), int(canvas_max_height))
            h, w = self.img.shape[:2]
            print(f"Original image: {self.original_image_dims[0]}x{self.original_image_dims[1]}")
            print(f"Resized image to: {w}x{h} for display.")

            # Set default map name based on filename
            base, _ = os.path.splitext(os.path.basename(self.filepath))
            # Sanitize name for Foundry (basic example: replace spaces/dots)
            sanitized_name = re.sub(r'[ .]+', '_', base)
            self.map_name_entry.delete(0, tk.END)
            self.map_name_entry.insert(0, sanitized_name)


            # Initial clear before processing
            self.clear_canvas() # Clear both canvases and reset data

            # Process and display
            self.process_image()

        except Exception as e:
            messagebox.showerror("Error Loading Image", f"Failed to load image:\n{e}", parent=self.master)
            self.img = None
            self.original_image_dims = (0, 0)
            self.clear_canvas()

    def clear_canvas(self):
        # Clear main canvas (Original + Overlays)
        if self.canvas:
            self.canvas.delete("all")
            try:
                # Use parent frame size to better estimate available space
                parent_frame = self.canvas.master
                parent_frame.update_idletasks()
                canvas_w = parent_frame.winfo_width()
                canvas_h = parent_frame.winfo_height()
                if canvas_w > 1 and canvas_h > 1:
                    self.canvas.create_text(canvas_w/2, canvas_h/2, text="Load image...", fill=COLOR_TEXT, anchor=tk.CENTER, font=('Segoe UI', 12))
            except Exception: pass # Ignore if canvas size is not available yet

        # Clear processed canvas
        if self.processed_canvas:
            self.processed_canvas.delete("all")
            try:
                parent_frame = self.processed_canvas.master
                parent_frame.update_idletasks()
                canvas_w = parent_frame.winfo_width()
                canvas_h = parent_frame.winfo_height()
                if canvas_w > 1 and canvas_h > 1:
                    self.processed_canvas.create_text(canvas_w/2, canvas_h/2, text="Processing view...", fill=COLOR_TEXT, anchor=tk.CENTER, font=('Segoe UI', 10))
            except Exception: pass

        # Reset derived image data
        self.processed_img = None
        self.intermediate_processed_img = None
        self.tk_img = None
        self.tk_processed_img = None

        # Reset detected elements and counts
        self.contours = []
        self.lines = []
        self.poly_count_label.config(text="Polygons: 0")
        self.line_count_label.config(text="Lines: 0")

    def resize_image(self, img, max_width, max_height):
        """Resizes image to fit within max dimensions, preserving aspect ratio. Does not scale up."""
        height, width = img.shape[:2]
        scale = 1.0
        if width > 0 and height > 0:
            # Calculate scale factor to fit within bounds, ensuring it's <= 1.0
            scale = min(max_width / width, max_height / height, 1.0)
        else: return img # Return original if dimensions are invalid

        if scale < 1.0: # Only resize if scaling down is needed
            new_width = max(1, int(width * scale))
            new_height = max(1, int(height * scale))
            # Use INTER_AREA for shrinking, generally gives good results
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        return img

    # --- Merge Logic (merge_lines, merge_polygons) - Keep as is ---
    # (merge_lines and merge_polygons methods remain unchanged)
    def merge_lines(self, lines, threshold):
        n = len(lines); parent = list(range(n))
        if n <= 1: return lines
        def find(i):
            if parent[i] == i: return i
            parent[i] = find(parent[i]); return parent[i]
        def union(i, j):
            root_i, root_j = find(i), find(j)
            if root_i != root_j: parent[root_j] = root_i
        endpoints = []; threshold_sq = threshold * threshold
        for i, (x1, y1, x2, y2) in enumerate(lines):
            endpoints.extend([(x1, y1, i), (x2, y2, i)])
        global KDTREE_AVAILABLE # Allow modification
        if KDTREE_AVAILABLE:
            try:
                pts = np.array([(pt[0], pt[1]) for pt in endpoints])
                if len(pts) < 2: return lines # KDTree needs at least 2 points
                tree = KDTree(pts); pairs = tree.query_pairs(r=threshold)
                for i, j in pairs:
                    li, lj = endpoints[i][2], endpoints[j][2]
                    if li != lj: union(li, lj)
            except Exception as e: print(f"KDTree error: {e}. Fallback."); KDTREE_AVAILABLE = False
        # Fallback or if KDTree is not available
        if not KDTREE_AVAILABLE:
            for i in range(len(endpoints)):
                x1, y1, li = endpoints[i]
                for j in range(i + 1, len(endpoints)):
                    x2, y2, lj = endpoints[j]
                    if li != lj and ((x1 - x2)**2 + (y1 - y2)**2 < threshold_sq): union(li, lj)
        # Group lines and find representative line for each group
        groups = {}; merged_lines = []
        for i in range(n): groups.setdefault(find(i), []).append(i)
        for group_indices in groups.values():
            if not group_indices: continue
            group_points = []
            for idx in group_indices: group_points.extend([(lines[idx][0], lines[idx][1]), (lines[idx][2], lines[idx][3])])
            if not group_points: continue
            max_dist_sq = -1; best_pair = (group_points[0], group_points[0])
            # Use convex hull to find the most distant points in the group as the new line ends
            if len(group_points) > 1:
                hull_points = cv2.convexHull(np.array(group_points, dtype=np.float32))
                if hull_points is not None and len(hull_points) > 1:
                     # Ensure hull_points is a list of points [[x,y], [x,y], ...]
                     hull_pts_list = hull_points.squeeze().tolist()
                     if isinstance(hull_pts_list[0], (int, float)): # Handle single point hull case
                        pts_to_check = [hull_pts_list] if len(hull_pts_list) == 2 else []
                     elif isinstance(hull_pts_list[0], list):
                         pts_to_check = hull_pts_list
                     else: pts_to_check = [] # Unexpected format

                     for i in range(len(pts_to_check)):
                         for j in range(i + 1, len(pts_to_check)):
                             p1, p2 = pts_to_check[i], pts_to_check[j]
                             dist_sq = (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2
                             if dist_sq > max_dist_sq: max_dist_sq = dist_sq; best_pair = (tuple(p1), tuple(p2))
                else: # Fallback if convex hull fails (e.g., collinear points)
                     for i in range(len(group_points)):
                         for j in range(i + 1, len(group_points)):
                             p1, p2 = group_points[i], group_points[j]
                             dist_sq = (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2
                             if dist_sq > max_dist_sq: max_dist_sq = dist_sq; best_pair = (p1, p2)

            merged_line = tuple(map(int, best_pair[0])) + tuple(map(int, best_pair[1]))
            # Ensure line has non-zero length after merging/rounding
            if merged_line[0] != merged_line[2] or merged_line[1] != merged_line[3]:
                merged_lines.append(merged_line)
        return merged_lines

    def merge_polygons(self, polygons, threshold):
        if not SHAPELY_AVAILABLE or len(polygons) <= 1: return polygons
        shapely_polys = []
        for poly_np in polygons:
             pts = poly_np.squeeze()
             if pts.ndim == 2 and pts.shape[0] >= 3: # Check shape before creating Polygon
                 try:
                     p = Polygon(pts)
                     if not p.is_valid: p = p.buffer(0) # Attempt to fix invalid polygon
                     if p.is_valid and not p.is_empty: shapely_polys.append(p)
                 except Exception as e: print(f"Shapely poly creation error: {e} for points {pts}"); continue
             # else: print(f"Skipping invalid polygon shape: ndim={pts.ndim}, shape={pts.shape}") # Debugging
        if not shapely_polys: return []
        try:
            # Buffer polygons outward
            buffered = [p.buffer(threshold, join_style=2) for p in shapely_polys if p.is_valid] # Use LINESTRING join style
            if not buffered: return []

            # Merge overlapping buffered polygons
            merged_buffered = unary_union(buffered)
            if merged_buffered.is_empty: return []

            final_polys_shapely = []
            geoms_to_process = []
            # Handle different geometry types resulting from union
            if merged_buffered.geom_type == 'Polygon': geoms_to_process = [merged_buffered]
            elif merged_buffered.geom_type == 'MultiPolygon': geoms_to_process = list(merged_buffered.geoms)
            elif merged_buffered.geom_type == 'GeometryCollection':
                # Extract only Polygons or MultiPolygons from the collection
                geoms_to_process = [g for g in merged_buffered.geoms if g.geom_type in ('Polygon', 'MultiPolygon')]
            # else: print(f"Unexpected geometry type after union: {merged_buffered.geom_type}") # Debugging

            # Buffer inward and collect final valid polygons
            for geom in geoms_to_process:
                 # Debuffer (buffer inward)
                 debuffered = geom.buffer(-threshold, join_style=2)
                 if debuffered.is_empty: continue

                 if debuffered.geom_type == 'Polygon':
                     if debuffered.is_valid and not debuffered.is_empty:
                         final_polys_shapely.append(debuffered)
                 elif debuffered.geom_type == 'MultiPolygon':
                      # Add valid polygons from the multipolygon
                     final_polys_shapely.extend(p for p in debuffered.geoms if p.geom_type == 'Polygon' and p.is_valid and not p.is_empty)
                 # else: print(f"Unexpected geometry type after debuffer: {debuffered.geom_type}") # Debugging


            merged_contours_np = []
            min_final_area = 1.0 # Minimum area for a polygon to be kept after merging/debuffering
            for p in final_polys_shapely:
                if p.is_valid and not p.is_empty and p.geom_type == 'Polygon' and p.area > min_final_area:
                    # Get exterior coordinates, convert to int32, reshape for OpenCV
                    coords = np.array(p.exterior.coords, dtype=np.int32)
                    # Ensure we have enough points and correct shape
                    if len(coords) >= 4: # Need at least 3 points + closing point from shapely
                       # Reshape to OpenCV contour format: (N, 1, 2)
                       # Exclude the last point (duplicate of the first) from shapely
                       merged_contours_np.append(coords[:-1].reshape((-1, 1, 2)))
                    # else: print(f"Skipping polygon with < 4 coords after merge: {len(coords)}") # Debugging
            return merged_contours_np

        except Exception as e:
            print(f"Shapely merge/buffer error: {e}");
            return polygons # Return original polygons on error
    # --- End Merge Logic ---

    def update_display(self):
        """Updates the main canvas (Original + Overlays)"""
        if self.img is None:
            self.clear_canvas() # Clear canvases if no image is loaded
            return

        display_img = self.img.copy() # Start with the original resized image

        # Draw Polygons if requested
        if self.show_polygons_var.get() and self.contours:
            try:
                # Convert hex color string to BGR tuple for OpenCV
                poly_color_rgb = tuple(int(COLOR_POLYGON.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                poly_color_bgr = poly_color_rgb[::-1]
                cv2.drawContours(display_img, self.contours, -1, poly_color_bgr, thickness=2) # Outline thickness 2
            except Exception as e:
                print(f"Error drawing polygons: {e}")

        # Draw Lines if requested
        if self.show_lines_var.get() and self.lines:
            try:
                line_color_rgb = tuple(int(COLOR_LINE.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                line_color_bgr = line_color_rgb[::-1]
                for (x1, y1, x2, y2) in self.lines:
                    cv2.line(display_img, (x1, y1), (x2, y2), line_color_bgr, 2) # Line thickness 2
            except Exception as e:
                print(f"Error drawing lines: {e}")

        self.processed_img = display_img # Store the image with overlays
        self.display_image_on_canvas(display_img, self.canvas, 'tk_img') # Display on the main canvas


    def display_image_on_canvas(self, img_to_display, target_canvas, tk_image_attr_name):
        """Displays the given BGR or Grayscale image on the specified canvas, storing the TkImage."""
        if img_to_display is None or target_canvas is None: return

        try:
            # Convert to RGB for PIL/Tkinter
            if len(img_to_display.shape) == 2: # Grayscale
                im_pil = PILImage.fromarray(img_to_display, mode='L')
            elif len(img_to_display.shape) == 3: # Assume BGR
                 im_pil = PILImage.fromarray(cv2.cvtColor(img_to_display, cv2.COLOR_BGR2RGB))
            else:
                 print("Unsupported image format for display")
                 return

            # Get target canvas dimensions (use parent frame for better accuracy before window mapped)
            parent_frame = target_canvas.master
            parent_frame.update_idletasks()
            canvas_w = parent_frame.winfo_width()
            canvas_h = parent_frame.winfo_height()

            if canvas_w <= 1 or canvas_h <= 1: # Canvas not realized yet, fallback
                canvas_w = im_pil.width
                canvas_h = im_pil.height
                # print(f"Canvas {tk_image_attr_name} not realized, using image size: {canvas_w}x{canvas_h}") # Debug
            # else: print(f"Canvas {tk_image_attr_name} realized size: {canvas_w}x{canvas_h}") # Debug


            # Resize PIL image to fit current canvas size while maintaining aspect ratio
            # Use LANCZOS for high quality downsampling
            img_aspect = im_pil.width / im_pil.height
            canvas_aspect = canvas_w / canvas_h

            if img_aspect > canvas_aspect: # Image is wider than canvas
                new_w = canvas_w
                new_h = max(1, int(new_w / img_aspect))
            else: # Image is taller than or same aspect as canvas
                new_h = canvas_h
                new_w = max(1, int(new_h * img_aspect))

            # Only resize if necessary
            if new_w != im_pil.width or new_h != im_pil.height:
                # print(f"Resizing PIL image for {tk_image_attr_name} to {new_w}x{new_h}") # Debug
                im_pil_resized = im_pil.resize((new_w, new_h), PILImage.Resampling.LANCZOS)
            else:
                im_pil_resized = im_pil # No resize needed


            # Create PhotoImage and store it using setattr
            tk_image = ImageTk.PhotoImage(image=im_pil_resized)
            setattr(self, tk_image_attr_name, tk_image) # Store reference e.g., self.tk_img = tk_image

            # Display on canvas
            target_canvas.delete("all")
            # Center the image within the canvas widget bounds
            x_pos = (target_canvas.winfo_reqwidth() - new_w) // 2 # Use reqwidth for centering
            y_pos = (target_canvas.winfo_reqheight() - new_h) // 2 # Use reqheight
            target_canvas.create_image(x_pos, y_pos, anchor=tk.NW, image=tk_image)
            # Update the canvas configuration to reflect the image size it's showing
            # target_canvas.config(width=new_w, height=new_h) # This might fight the grid layout, maybe remove

        except Exception as e:
            print(f"Canvas display error ({tk_image_attr_name}): {e}")
            if target_canvas: target_canvas.delete("all")
            try: target_canvas.create_text(10, 10, anchor=tk.NW, text="Error display", fill="red")
            except: pass


    def display_intermediate_on_canvas(self, img_to_display):
        """Displays the intermediate (usually grayscale) image on the processed canvas"""
        # Use the general display function
        self.display_image_on_canvas(img_to_display, self.processed_canvas, 'tk_processed_img')


    def save_display_image(self):
        """Saves the image shown on the main canvas (original + overlays)"""
        if self.processed_img is None:
            messagebox.showwarning("Warning", "No overlay image to save!", parent=self.master)
            return

        # Suggest a filename based on the original
        default_name = "processed_image.png"
        if self.filepath:
            base, ext = os.path.splitext(os.path.basename(self.filepath))
            default_name = f"{base}_overlay{ext}"

        path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg"), ("Bitmap", "*.bmp")],
            title="Save Overlay Image",
            parent=self.master
        )
        if path:
            try:
                # Save the internally stored processed image (which matches overlays)
                cv2.imwrite(path, self.processed_img)
                messagebox.showinfo("Saved", f"Overlay image saved to\n{path}", parent=self.master)
            except Exception as e:
                messagebox.showerror("Error Saving", f"Could not save image:\n{e}", parent=self.master)

    def _get_export_params(self):
        """Helper to get common parameters for export/sending."""
        cookie_id = self.cookie_id_entry.get()
        map_name = self.map_name_entry.get()
        if not cookie_id or not map_name:
            messagebox.showerror("Error", "Please enter both Cookie ID and Map Name.", parent=self.master)
            return None

        if not self.filepath or not os.path.exists(self.filepath):
            messagebox.showerror("Error", "Original image path is invalid or missing. Please load image again.", parent=self.master)
            return None

        if self.img is None or self.original_image_dims == (0,0):
             messagebox.showerror("Error", "Image data missing. Please load image.", parent=self.master)
             return None

        try:
            # Get scale factors from sliders (value is % * 10), divide by 1000 for actual scale
            x_scale = float(self.slider_widgets['x_scale_factor']['scale'].get()) / 1000.0
            y_scale = float(self.slider_widgets['y_scale_factor']['scale'].get()) / 1000.0
        except (KeyError, ValueError, tk.TclError) as e:
             messagebox.showerror("Error", f"Invalid scale factor setting: {e}", parent=self.master)
             return None

        return {
            "cookie_id": cookie_id,
            "map_name": map_name,
            "image_path": self.filepath,
            "x_scale": x_scale,
            "y_scale": y_scale,
            "original_width": self.original_image_dims[0],
            "original_height": self.original_image_dims[1],
            "resized_width": self.img.shape[1],
            "resized_height": self.img.shape[0],
        }


    def create_wall_from_line(self):
        params = self._get_export_params()
        if not params: return

        if not self.lines:
             messagebox.showwarning("Warning", "No lines detected to send.", parent=self.master)
             return

        warnings, data = self._export_data(False, True) # Only export lines
        if not data.get("lines"):
             # _export_data should have formatted them correctly if self.lines exists
             messagebox.showerror("Error", "Failed to format line data for sending.", parent=self.master)
             return

        print(f"Sending lines for map '{params['map_name']}' with cookie '{params['cookie_id']}'...")
        try:
            # Pass scaling factors to send_token
            send_token(params['cookie_id'], params['image_path'], data, params['map_name'],
                       params['x_scale'], params['y_scale'])
            messagebox.showinfo("Sent", f"Line data sent for map '{params['map_name']}'. Check Foundry VTT.", parent=self.master)
        except Exception as e:
             messagebox.showerror("Send Error", f"Failed to send line data:\n{e}", parent=self.master)


    def create_wall_from_polygon(self):
        params = self._get_export_params()
        if not params: return

        if not self.contours:
             messagebox.showwarning("Warning", "No polygons detected to send.", parent=self.master)
             return

        warnings, data = self._export_data(True, False) # Only export polygons
        if not data.get("polygons"):
             messagebox.showerror("Error", "Failed to format polygon data for sending.", parent=self.master)
             return

        print(f"Sending polygons for map '{params['map_name']}' with cookie '{params['cookie_id']}'...")
        try:
             # Pass scaling factors to send_token (even if polygons dont use them directly, API might)
            send_token(params['cookie_id'], params['image_path'], data, params['map_name'],
                       params['x_scale'], params['y_scale'])
            messagebox.showinfo("Sent", f"Polygon data sent for map '{params['map_name']}'. Check Foundry VTT.", parent=self.master)
        except Exception as e:
             messagebox.showerror("Send Error", f"Failed to send polygon data:\n{e}", parent=self.master)


    def _export_data(self, save_polygons=True, save_lines=True):
        """Prepares polygon and line data for export, converting coordinates if necessary."""
        data = {}; warnings = []

        # Calculate scaling factors needed to convert resized coordinates back to original
        resize_scale_x = 1.0
        resize_scale_y = 1.0
        if self.img is not None and self.original_image_dims[0] > 0 and self.original_image_dims[1] > 0:
             resized_width = self.img.shape[1]
             resized_height = self.img.shape[0]
             if resized_width > 0: resize_scale_x = self.original_image_dims[0] / resized_width
             if resized_height > 0: resize_scale_y = self.original_image_dims[1] / resized_height

        # Prepare Polygon Data (scaled back to original image coordinates)
        if save_polygons:
            poly_list_original_coords = []
            if self.contours:
                for poly in self.contours:
                    try:
                        # Squeeze to remove single dimension entry, get list of points
                        pts_resized = poly.squeeze().tolist()
                        if not isinstance(pts_resized, list): continue # Skip if not list

                        # Handle case where squeeze might return a single point [x, y]
                        if len(pts_resized) > 0 and isinstance(pts_resized[0], (int, float)):
                             if len(pts_resized) == 2: pts_resized = [pts_resized] # Wrap single point
                             else: continue # Malformed

                        # Scale points back to original coordinates
                        pts_original = []
                        for pt in pts_resized:
                            if isinstance(pt, list) and len(pt) == 2:
                                orig_x = round(pt[0] * resize_scale_x)
                                orig_y = round(pt[1] * resize_scale_y)
                                pts_original.append([orig_x, orig_y])
                            # else: print(f"Skipping invalid point in polygon: {pt}") # Debug

                        if len(pts_original) >= 3: # Need at least 3 points for polygon
                            poly_list_original_coords.append(pts_original)
                        # else: print(f"Polygon had < 3 valid points after scaling: {pts_original}") # Debug

                    except Exception as e:
                        print(f"Polygon export formatting/scaling error: {e} on polygon shape: {poly.shape}"); continue

                if not poly_list_original_coords and self.contours:
                    warnings.append("Polygon export: Failed to format/scale detected polygons.")
            elif save_polygons: # No contours detected, but polygon export requested
                 if not (save_lines and self.lines): # Avoid duplicate warning if lines also empty
                    warnings.append("Polygon export: No polygons detected.")

            data["polygons"] = poly_list_original_coords # List of lists of [x,y] pairs in original coords

        # Prepare Line Data (scaled back to original image coordinates)
        if save_lines:
            line_list_original_coords = []
            if self.lines:
                 for (x1_r, y1_r, x2_r, y2_r) in self.lines:
                      # Scale points back to original coordinates
                      orig_x1 = round(x1_r * resize_scale_x)
                      orig_y1 = round(y1_r * resize_scale_y)
                      orig_x2 = round(x2_r * resize_scale_x)
                      orig_y2 = round(y2_r * resize_scale_y)
                      # Keep format as tuple: (x1, y1, x2, y2) but with original coords
                      line_list_original_coords.append((orig_x1, orig_y1, orig_x2, orig_y2))

                 if not line_list_original_coords and self.lines:
                      warnings.append("Line export: Failed to format/scale detected lines.")
            elif save_lines: # No lines detected, but line export requested
                 if not (save_polygons and data.get("polygons")): # Avoid duplicate warning
                    warnings.append("Line export: No lines detected.")

            data["lines"] = line_list_original_coords # List of (x1, y1, x2, y2) tuples in original coords

        return warnings, data


    def export_json(self, save_polygons=True, save_lines=True):
        """Exports detected polygons/lines (in original image coordinates) to a JSON file."""
        warnings , data = self._export_data(save_polygons, save_lines)

        final_data_present = data.get("polygons") or data.get("lines")

        if warnings:
            messagebox.showwarning("Export Warning", "\n".join(warnings), parent=self.master)

        if not final_data_present:
            messagebox.showinfo("Info", "Nothing to export.", parent=self.master)
            return

        # Add metadata to JSON (optional but helpful)
        export_metadata = {
            "source_file": self.filepath,
            "original_dimensions": {"width": self.original_image_dims[0], "height": self.original_image_dims[1]}
        }
        final_export_data = {
             "metadata": export_metadata,
             "walls": data # Embed the polygon/line data under a 'walls' key perhaps
        }


        # Suggest a filename based on the original
        default_name = "map_data.json"
        if self.filepath:
            base, _ = os.path.splitext(os.path.basename(self.filepath))
            default_name = f"{base}_walls.json"

        path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            title="Save Wall Data (JSON)",
            parent=self.master
        )
        if path:
            try:
                with open(path, "w") as f:
                    json.dump(final_export_data, f, indent=4) # Use the data with metadata
                messagebox.showinfo("Saved", f"Wall data saved successfully to\n{path}", parent=self.master)
            except Exception as e:
                messagebox.showerror("Error Saving JSON", f"Could not save JSON data:\n{e}", parent=self.master)

# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = WallLineDetectorApp(root)
    # Increase minimum size slightly more to ensure controls fit
    root.minsize(1200, 700)
    # Call clear_canvas shortly after startup to ensure canvas sizes are known
    root.after(150, app.clear_canvas)
    root.mainloop()