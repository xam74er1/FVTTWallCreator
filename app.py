import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk  # Import ttk for themed widgets
from tkinter import filedialog, messagebox
from tkinter.ttk import Style # Import Style for theme configuration
from PIL import Image, ImageTk, Image as PILImage # Use alias
import json
import re # For input validation

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

        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(1, weight=1) # Canvas column expands

        self.img = None
        self.processed_img = None
        self.tk_img = None

        self.contours = []
        self.lines = []

        self.lsd = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD)

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

        # Entry Styling (Requires configuring the base 'TEntry')
        self.style.configure('TEntry',
                             fieldbackground=COLOR_ENTRY_BG, # Background color when editable
                             foreground=COLOR_ENTRY_TEXT,    # Text color
                             insertcolor=COLOR_TEXT,         # Cursor color
                             borderwidth=1,
                             relief=tk.FLAT)
        self.style.map('TEntry',
                       # Add a subtle border highlight on focus
                       bordercolor=[('focus', COLOR_ACCENT)],
                       fieldbackground=[('disabled', COLOR_SECONDARY_BG)],
                       foreground=[('disabled', COLOR_DISABLED_TEXT)])

        # Separator
        self.style.configure('TSeparator', background=COLOR_SECONDARY_BG)

        # Store references to widgets needed for updates
        self.slider_widgets = {} # Dictionary to hold {'name': {'scale': ttk.Scale, 'label': ttk.Label, 'entry': ttk.Entry, 'var': tk.StringVar}}

        # Debounce Timer
        self._debounce_timer = None

        # Create UI
        self.create_widgets()


    def create_widgets(self):
        control_frame = ttk.Frame(self.master, padding="15 15 15 15")
        control_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        # Configure columns in control_frame: 0=Label, 1=Scale (expand), 2=Value/Entry
        control_frame.columnconfigure(0, weight=0)
        control_frame.columnconfigure(1, weight=1) # Scale column expands
        control_frame.columnconfigure(2, weight=0, minsize=50) # Fixed size for entry area

        row_idx = 0

        def add_separator():
            nonlocal row_idx
            sep = ttk.Separator(control_frame, orient=tk.HORIZONTAL)
            sep.grid(row=row_idx, column=0, columnspan=3, sticky="ew", pady=(15, 10)) # Span 3 columns now
            row_idx += 1

        # --- File Operations ---
        ttk.Label(control_frame, text="File", style='Bold.TLabel').grid(row=row_idx, column=0, columnspan=3, sticky="w", pady=(0, 5))
        row_idx += 1
        self.load_button = ttk.Button(control_frame, text="Load Image", command=self.load_image)
        self.load_button.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=3, sticky="ew")
        row_idx += 1
        self.save_button = ttk.Button(control_frame, text="Save Display", command=self.save_display_image)
        self.save_button.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=3, sticky="ew")
        row_idx += 1

        add_separator()

        # --- Export ---
        ttk.Label(control_frame, text="Export", style='Bold.TLabel').grid(row=row_idx, column=0, columnspan=3, sticky="w", pady=(0, 5))
        row_idx += 1
        self.export_lines_button = ttk.Button(control_frame, text="Export Lines",
                                             command=lambda: self.export_json(save_polygons=False, save_lines=True))
        self.export_lines_button.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=3, sticky="ew")
        row_idx += 1
        self.export_polygons_button = ttk.Button(control_frame, text="Export Polygons",
                                                command=lambda: self.export_json(save_polygons=True, save_lines=False))
        self.export_polygons_button.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=3, sticky="ew")
        row_idx += 1

        add_separator()

        # --- Display Options & Counts ---
        ttk.Label(control_frame, text="Display", style='Bold.TLabel').grid(row=row_idx, column=0, columnspan=3, sticky="w", pady=(0, 5))
        row_idx += 1
        self.show_polygons_var = tk.BooleanVar(value=True)
        self.show_lines_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame, text="Show Polygons", variable=self.show_polygons_var,
                       command=self.update_display).grid(row=row_idx, column=0, columnspan=3, sticky="w", padx=5, pady=1)
        row_idx += 1
        ttk.Checkbutton(control_frame, text="Show Lines", variable=self.show_lines_var, command=self.update_display).grid(
            row=row_idx, column=0, columnspan=3, sticky="w", padx=5, pady=1)
        row_idx += 1
        self.poly_count_label = ttk.Label(control_frame, text="Polygons: 0")
        self.poly_count_label.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=(5, 0), sticky="w")
        row_idx += 1
        self.line_count_label = ttk.Label(control_frame, text="Lines: 0")
        self.line_count_label.grid(row=row_idx, column=0, columnspan=3, padx=5, pady=(0, 5), sticky="w")
        row_idx += 1

        add_separator()

        # --- Detection Parameters ---
        ttk.Label(control_frame, text="Detection Params", style='Bold.TLabel').grid(row=row_idx, column=0, columnspan=3, sticky="w", pady=(0, 5))
        row_idx += 1

        # --- Helper to create label + scale + value/entry ---
        def add_slider_control(name, label_text, from_val, to_val, default_val, is_epsilon=False):
            nonlocal row_idx
            # Description Label
            ttk.Label(control_frame, text=label_text).grid(row=row_idx, column=0, sticky="w", padx=(5, 10))

            # Scale
            scale = ttk.Scale(control_frame, from_=from_val, to=to_val, orient=tk.HORIZONTAL)
            scale.set(default_val)
            scale.grid(row=row_idx, column=1, sticky="ew", padx=5, pady=1)

            # Entry & Value Display Frame
            entry_frame = ttk.Frame(control_frame) # Frame to hold Entry and optional % sign
            entry_frame.grid(row=row_idx, column=2, sticky="ew", padx=(5, 0))
            entry_frame.columnconfigure(0, weight=1) # Entry expands

            # Entry Variable
            entry_var = tk.StringVar()

            # Entry Widget
            entry = ttk.Entry(entry_frame, textvariable=entry_var, width=5, justify='right')
            entry.grid(row=0, column=0, sticky='ew')

            # Optional Unit Label (e.g., '%')
            if is_epsilon:
                 ttk.Label(entry_frame, text="%", style='Value.TLabel').grid(row=0, column=1, sticky='w', padx=(1,0))

            # Store widgets
            self.slider_widgets[name] = {'scale': scale, 'entry': entry, 'var': entry_var, 'from': from_val, 'to': to_val, 'is_epsilon': is_epsilon}

            # Set initial display value
            self.update_value_display(name)

            # --- Binding ---
            # Slider changes -> update entry & process (debounced)
            scale.config(command=lambda val, n=name: self.handle_slider_change(val, n))
            # Entry changes -> update slider (on Enter or FocusOut)
            entry.bind("<Return>", lambda event, n=name: self.handle_entry_change(event, n))
            entry.bind("<FocusOut>", lambda event, n=name: self.handle_entry_change(event, n))
            entry.bind("<KP_Enter>", lambda event, n=name: self.handle_entry_change(event, n)) # Numpad Enter

            row_idx += 1
            return scale # Return scale for direct access if needed (like disabling)

        # Create sliders using the helper
        add_slider_control('canny1', "Canny Thresh 1", 0, 500, 50)
        add_slider_control('canny2', "Canny Thresh 2", 0, 500, 150)
        add_slider_control('epsilon', "Approx. Eps (%)", 1, 100, 20, is_epsilon=True) # Range 1-100, display as 0.1-10.0
        add_slider_control('blur', "Blur Kernel", 1, 10, 2)
        add_slider_control('morph', "Morph Kernel", 0, 5, 0)
        add_slider_control('area', "Min Area", 0, 2000, 100)

        add_separator()

        # --- Merge Options ---
        ttk.Label(control_frame, text="Merging", style='Bold.TLabel').grid(row=row_idx, column=0, columnspan=3, sticky="w", pady=(0, 5))
        row_idx += 1

        # --- Checkbuttons (Simpler: Don't need direct input for threshold, maybe add later if needed) ---
        self.merge_lines_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame, text="Merge Close Lines", variable=self.merge_lines_var,
                       command=self.process_image_debounced).grid(row=row_idx, column=0, columnspan=3, sticky="w", padx=5, pady=1)
        row_idx += 1
        add_slider_control('line_thresh', "Line Thresh", 1, 100, 20)


        self.merge_polygons_var = tk.BooleanVar(value=False)
        self.poly_merge_check = ttk.Checkbutton(control_frame, text="Merge Close Polygons", variable=self.merge_polygons_var,
                       command=self.process_image_debounced)
        self.poly_merge_check.grid(row=row_idx, column=0, columnspan=3, sticky="w", padx=5, pady=1)
        row_idx += 1
        poly_thresh_scale = add_slider_control('poly_thresh', "Poly Thresh", 1, 100, 20)


        # Disable polygon merging controls if shapely is missing
        if not SHAPELY_AVAILABLE:
            self.merge_polygons_var.set(False)
            self.poly_merge_check.config(state=tk.DISABLED)
            # Disable the Scale, Entry, and Label for poly_thresh
            widgets = self.slider_widgets.get('poly_thresh')
            if widgets:
                widgets['scale'].config(state=tk.DISABLED)
                widgets['entry'].config(state=tk.DISABLED)
                # Optionally grey out the description label too
                # (Need to store label ref in add_slider_control or find it)
            ttk.Label(control_frame, text="(Requires Shapely)", font="-size 8", foreground=COLOR_DISABLED_TEXT).grid(row=row_idx-2, column=1, columnspan=2, sticky='e', padx=5)

        # Add empty row at bottom to push controls up
        control_frame.rowconfigure(row_idx, weight=1)

        # --- Canvas (on the right) ---
        self.canvas = tk.Canvas(self.master, width=600, height=600, bg=COLOR_CANVAS_BG, highlightthickness=0)
        self.canvas.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)


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

        current_entry_text = entry_var.get()

        try:
            # Attempt to convert entry text to a float first for validation
            numeric_value = float(current_entry_text)

            # Handle epsilon scaling (input is %, scale needs integer 1-100)
            if is_epsilon:
                target_scale_val = numeric_value * 10.0 # e.g., 2.5% -> 25
            else:
                target_scale_val = numeric_value

            # Clamp the value to the slider's range
            clamped_scale_val = max(from_val, min(to_val, target_scale_val))

            # Round to nearest integer for the scale if not epsilon
            # For epsilon, allow rounding after clamping (e.g., 25.3 -> 25)
            final_scale_val = round(clamped_scale_val)

            # Update the slider (this will trigger handle_slider_change -> update_value_display -> debounce)
            scale.set(final_scale_val)

            # Optional: Force entry update immediately after validation/clamping
            # This corrects the entry if the user typed something out of range or non-integer
            # self.update_value_display(widget_name) # Already called by scale.set() via handle_slider_change

        except ValueError:
            # Invalid input (not a number), revert entry to current slider value
            print(f"Invalid input: '{current_entry_text}'. Reverting.")
            self.update_value_display(widget_name) # Revert entry to match slider

    def update_value_display(self, widget_name):
        """Updates the Entry text based on the current Slider value."""
        widgets = self.slider_widgets.get(widget_name)
        if not widgets: return

        scale = widgets['scale']
        entry_var = widgets['var']
        is_epsilon = widgets['is_epsilon']

        # Get integer value from scale
        scale_value = scale.get() # This might be float from internal ttk state, round it
        int_scale_value = round(float(scale_value)) # Ensure it's treated as integer base

        # Format for display
        if is_epsilon:
            display_value = f"{int_scale_value / 10.0:.1f}" # Display as float with 1 decimal place
        else:
            display_value = f"{int_scale_value}" # Display as integer

        # Update the Entry's variable
        entry_var.set(display_value)


    # --- Debounce mechanism ---
    def process_image_debounced(self, event=None):
        if self._debounce_timer is not None:
            self.master.after_cancel(self._debounce_timer)
        self._debounce_timer = self.master.after(250, self.process_image)

    # --- Core Processing ---
    def process_image(self, event=None):
        self._debounce_timer = None
        if self.img is None: return

        # Retrieve parameters *from sliders* using the stored widget references
        try:
            thresh1 = int(round(float(self.slider_widgets['canny1']['scale'].get())))
            thresh2 = int(round(float(self.slider_widgets['canny2']['scale'].get())))
            # Get epsilon scale value (1-100), convert to float 0.1-10.0, then to fraction
            epsilon_scale_val = round(float(self.slider_widgets['epsilon']['scale'].get()))
            epsilon_percent = (epsilon_scale_val / 10.0) / 100.0
            blur_factor = int(round(float(self.slider_widgets['blur']['scale'].get())))
            kernel_size = max(1, 2 * blur_factor + 1)
            morph_factor = int(round(float(self.slider_widgets['morph']['scale'].get())))
            morph_size = 2 * morph_factor + 1 if morph_factor > 0 else 0
            min_area = int(round(float(self.slider_widgets['area']['scale'].get())))

            do_merge_lines = self.merge_lines_var.get()
            line_merge_thresh = round(float(self.slider_widgets['line_thresh']['scale'].get()))

            do_merge_polygons = self.merge_polygons_var.get() and SHAPELY_AVAILABLE
            poly_merge_thresh = 0
            if SHAPELY_AVAILABLE: # Avoid error if disabled
                 poly_merge_thresh = round(float(self.slider_widgets['poly_thresh']['scale'].get()))

        except (ValueError, tk.TclError, KeyError) as e:
            print(f"Warning: Error getting slider value during processing: {e}")
            return

        # --- Image Processing Core --- (Identical to previous version)
        gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (kernel_size, kernel_size), 0)
        edges = cv2.Canny(blurred, thresh1, thresh2)

        edges_for_poly = edges.copy()
        if morph_factor > 0 and morph_size > 0:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (morph_size, morph_size))
            edges_for_poly = cv2.dilate(edges_for_poly, kernel, iterations=1)

        # Polygon detection
        contours_raw, _ = cv2.findContours(edges_for_poly, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        poly_list = []
        for cnt in contours_raw:
            if len(cnt) < 3: continue
            perimeter = cv2.arcLength(cnt, True)
            if perimeter == 0: continue
            epsilon = epsilon_percent * perimeter
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            if len(approx) >= 3 and cv2.contourArea(approx) > min_area:
                 poly_list.append(approx)

        if do_merge_polygons:
            poly_list = self.merge_polygons(poly_list, poly_merge_thresh)
        self.contours = poly_list

        # Line detection
        detected_lines = self.lsd.detect(edges)
        line_list = []
        if detected_lines is not None and detected_lines[0] is not None:
            min_line_length_sq = 5**2 # Minimum line length (squared) to avoid tiny segments
            for dline in detected_lines[0]:
                x1, y1, x2, y2 = map(int, dline[0])
                # Check length before adding
                if (x2-x1)**2 + (y2-y1)**2 >= min_line_length_sq:
                    line_list.append((x1, y1, x2, y2))

        if do_merge_lines:
            line_list = self.merge_lines(line_list, line_merge_thresh)
        self.lines = line_list

        # Update counts and display
        self.poly_count_label.config(text=f"Polygons: {len(self.contours)}")
        self.line_count_label.config(text=f"Lines: {len(self.lines)}")
        self.update_display()


    # --- Methods (Load, Clear, Resize, Merge, Display, Save, Export) ---
    # Keep these methods largely the same as the previous version
    # Make sure messagebox/filedialog use parent=self.master

    def load_image(self):
        filepath = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
        if not filepath: return
        try:
            img = cv2.imread(filepath)
            if img is None: raise ValueError("File could not be read by OpenCV.")
            max_w = self.master.winfo_screenwidth() * 0.6
            max_h = self.master.winfo_screenheight() * 0.8
            self.img = self.resize_image(img, int(max_w), int(max_h))
            self.process_image() # Process immediately
            # self.update_display() # Called by process_image
        except Exception as e:
            messagebox.showerror("Error Loading Image", f"Failed to load image: {e}", parent=self.master)
            self.img = None; self.clear_canvas()

    def clear_canvas(self):
        self.canvas.delete("all")
        try:
             canvas_w = self.canvas.winfo_width(); canvas_h = self.canvas.winfo_height()
             if canvas_w > 1 and canvas_h > 1:
                 self.canvas.create_text(canvas_w/2, canvas_h/2, text="Load an image...", fill=COLOR_TEXT, anchor=tk.CENTER)
        except Exception: pass
        self.img = None; self.processed_img = None; self.tk_img = None
        self.contours = []; self.lines = []
        self.poly_count_label.config(text="Polygons: 0")
        self.line_count_label.config(text="Lines: 0")

    def resize_image(self, img, max_width, max_height):
        height, width = img.shape[:2]; scale = 1.0
        if width > 0 and height > 0 : scale = min(max_width / width, max_height / height, 1.0)
        if scale < 1.0:
            new_width = max(1, int(width * scale)); new_height = max(1, int(height * scale))
            img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        return img

    # --- Merge Logic (merge_lines, merge_polygons) - Keep as is ---
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
                     # Squeeze to remove unnecessary dimensions
                     hull_pts_list = hull_points.squeeze().tolist()
                     pts_to_check = []
                     # Ensure it's a list of lists (handle potential single-point or weird returns)
                     if isinstance(hull_pts_list[0], list): pts_to_check = hull_pts_list
                     else: pts_to_check = [hull_pts_list]

                     # Check pairwise distance only on hull points for efficiency
                     for i in range(len(pts_to_check)):
                         for j in range(i + 1, len(pts_to_check)):
                             p1, p2 = pts_to_check[i], pts_to_check[j]
                             dist_sq = (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2
                             if dist_sq > max_dist_sq: max_dist_sq = dist_sq; best_pair = (tuple(p1), tuple(p2))
                else: # Fallback if convex hull fails (e.g., all points collinear)
                     # Check all pairs in the original group points
                     for i in range(len(group_points)):
                         for j in range(i + 1, len(group_points)):
                             p1, p2 = group_points[i], group_points[j]
                             dist_sq = (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2
                             if dist_sq > max_dist_sq: max_dist_sq = dist_sq; best_pair = (p1, p2)

            # Create the final merged line from the best pair found
            merged_line = tuple(map(int, best_pair[0])) + tuple(map(int, best_pair[1]))
            merged_lines.append(merged_line)
        return merged_lines

    def merge_polygons(self, polygons, threshold):
        if not SHAPELY_AVAILABLE or len(polygons) <= 1: return polygons
        shapely_polys = []
        for poly_np in polygons:
             # Squeeze to get (N, 2) array
             pts = poly_np.squeeze()
             # Ensure it's a valid polygon structure
             if pts.ndim == 2 and pts.shape[0] >= 3:
                 try:
                     p = Polygon(pts)
                     # Attempt to fix invalid polygons (like self-intersections)
                     if not p.is_valid: p = p.buffer(0)
                     if p.is_valid and not p.is_empty: shapely_polys.append(p)
                 except Exception as e: print(f"Shapely poly creation error: {e}"); continue
        if not shapely_polys: return [] # Return empty if no valid polygons were created
        try:
            # Buffer polygons outwards
            buffered = [p.buffer(threshold, join_style=2) for p in shapely_polys] # MITRE join style
            # Merge overlapping buffered polygons
            merged_buffered = unary_union(buffered)
            if merged_buffered.is_empty: return []
            # Debuffer the merged shapes inwards to get final polygons
            final_polys_shapely = []
            geoms_to_process = []
            # Handle different geometry types resulting from unary_union
            if merged_buffered.geom_type == 'Polygon': geoms_to_process = [merged_buffered]
            elif merged_buffered.geom_type == 'MultiPolygon': geoms_to_process = list(merged_buffered.geoms)
            elif merged_buffered.geom_type == 'GeometryCollection':
                # Only process Polygon/MultiPolygon parts of a collection
                geoms_to_process = [g for g in merged_buffered.geoms if g.geom_type in ('Polygon', 'MultiPolygon')]

            for geom in geoms_to_process:
                 debuffered = geom.buffer(-threshold, join_style=2)
                 if debuffered.is_empty: continue
                 # Handle results of debuffering
                 if debuffered.geom_type == 'Polygon': final_polys_shapely.append(debuffered)
                 elif debuffered.geom_type == 'MultiPolygon':
                     # Add individual valid polygons from a MultiPolygon result
                     final_polys_shapely.extend(list(p for p in debuffered.geoms if not p.is_empty and p.geom_type == 'Polygon'))

            # Convert back to OpenCV contour format (list of numpy arrays)
            merged_contours_np = []
            for p in final_polys_shapely:
                # Ensure final polygon is valid, not empty, and has some area
                if p.is_valid and not p.is_empty and p.geom_type == 'Polygon' and p.area > 1.0: # Small area threshold
                    # Get exterior coordinates as numpy array
                    coords = np.array(p.exterior.coords, dtype=np.int32)
                    # Check if enough points exist (exterior coords include duplicate end point)
                    if len(coords) >= 4:
                       # Reshape to OpenCV contour format: (N, 1, 2), excluding duplicate end point
                       merged_contours_np.append(coords[:-1].reshape((-1, 1, 2)))
            return merged_contours_np
        except Exception as e:
            print(f"Shapely merge/buffer error: {e}");
            return polygons # Return original polygons on error

    def update_display(self):
        if self.img is None: self.clear_canvas(); return
        display_img = self.img.copy()
        # Draw Polygons
        if self.show_polygons_var.get() and self.contours:
            # Get BGR color from hex
            poly_color_rgb = tuple(int(c) for c in PILImage.new("RGB", (1, 1), COLOR_POLYGON).getpixel((0, 0)))
            poly_color_bgr = poly_color_rgb[::-1] # Convert RGB to BGR for OpenCV
            cv2.polylines(display_img, self.contours, isClosed=True, color=poly_color_bgr, thickness=2)
        # Draw Lines
        if self.show_lines_var.get() and self.lines:
             # Get BGR color from hex
            line_color_rgb = tuple(int(c) for c in PILImage.new("RGB", (1, 1), COLOR_LINE).getpixel((0, 0)))
            line_color_bgr = line_color_rgb[::-1] # Convert RGB to BGR for OpenCV
            for (x1, y1, x2, y2) in self.lines: cv2.line(display_img, (x1, y1), (x2, y2), line_color_bgr, 2)
        self.processed_img = display_img # Store the image with overlays
        self.display_image_on_canvas(display_img)

    def display_image_on_canvas(self, img_to_display):
        try:
            # Convert BGR (OpenCV) to RGB (PIL/Tkinter)
            rgb = cv2.cvtColor(img_to_display, cv2.COLOR_BGR2RGB)
            im_pil = PILImage.fromarray(rgb)
            # Resize image to fit canvas while maintaining aspect ratio
            canvas_w = self.canvas.winfo_width(); canvas_h = self.canvas.winfo_height()
            # Only resize if canvas has a valid size (winfo_width/height can be 1 initially)
            if canvas_w > 1 and canvas_h > 1: im_pil.thumbnail((canvas_w, canvas_h), PILImage.LANCZOS)
            # Convert PIL image to Tkinter PhotoImage
            self.tk_img = ImageTk.PhotoImage(image=im_pil)
            # Update canvas
            self.canvas.delete("all")
            self.canvas.config(width=im_pil.width, height=im_pil.height) # Adjust canvas size to scaled image
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        except Exception as e:
            print(f"Canvas display error: {e}"); self.canvas.delete("all")
            # Attempt to show error message on canvas itself
            try: self.canvas.create_text(10, 10, anchor=tk.NW, text="Error displaying image", fill="red")
            except: pass # Ignore if canvas is not ready

    def save_display_image(self):
        if self.processed_img is None: messagebox.showwarning("Warning", "No image to save!", parent=self.master); return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg")], title="Save Display Image", parent=self.master)
        if path:
            try: cv2.imwrite(path, self.processed_img); messagebox.showinfo("Saved", f"Image saved to\n{path}", parent=self.master)
            except Exception as e: messagebox.showerror("Error Saving", f"Could not save image:\n{e}", parent=self.master)

    def export_json(self, save_polygons=True, save_lines=True):
        data = {}; warnings = []
        # Prepare Polygon Data
        if save_polygons:
            poly_list = []
            for poly in self.contours:
                try:
                    # Convert numpy array to simple list of [x, y] pairs
                    pts = poly.squeeze().tolist()
                    # Basic validation: Ensure it's a list of lists (coordinates)
                    if isinstance(pts, list) and len(pts) > 0 and isinstance(pts[0], list): poly_list.append(pts)
                except Exception as e: print(f"Polygon export formatting error: {e}"); continue
            # Add warnings if needed
            if not poly_list and self.contours: warnings.append("Polygon export: Failed to format detected polygons for export.")
            elif not poly_list and not self.contours and save_polygons and not save_lines: warnings.append("Polygon export: No polygons were detected.")
            data["polygons"] = poly_list

        # Prepare Line Data
        if save_lines:
            # Add warning if no lines detected and lines were requested (and polygons weren't the only thing requested/present)
            if not self.lines and save_lines and not (save_polygons and data.get("polygons")): warnings.append("Line export: No lines were detected.")
            # Lines are already in a simple list of tuples format (x1, y1, x2, y2)
            data["lines"] = self.lines

        # Check if there's anything actually to save
        final_data_present = data.get("polygons") or data.get("lines")

        # Show warnings accumulated
        if warnings: messagebox.showwarning("Export Warning", "\n".join(warnings), parent=self.master)

        # Prevent saving an empty file if nothing was exported
        if not final_data_present:
            messagebox.showinfo("Info", "Nothing to export.", parent=self.master); return

        # Ask for save location
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], title="Save JSON Data", parent=self.master)
        if path:
            try:
                # Write data to JSON file
                with open(path, "w") as f: json.dump(data, f, indent=4)
                messagebox.showinfo("Saved", f"Data saved successfully to\n{path}", parent=self.master)
            except Exception as e: messagebox.showerror("Error Saving JSON", f"Could not save JSON data:\n{e}", parent=self.master)

# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = WallLineDetectorApp(root)
    root.minsize(850, 650) # Set a minimum size for the window
    # Call clear_canvas shortly after startup to ensure canvas size is known
    root.after(100, app.clear_canvas)
    root.mainloop()