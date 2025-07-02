import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox, font
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import json
import math


class TextLayer:
    def __init__(self, x=0, y=0, text="", font_path="", color="#000000"):
        self.x = x
        self.y = y
        self.text = text
        self.font_path = font_path
        self.color = color
        self.selected = False
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0


class PixelTextEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixel Perfect Text Editor")
        self.root.geometry("1200x800")

        # Initialize variables
        self.image = None
        self.display_image = None
        self.image_tk = None
        self.canvas_image = None
        self.zoom_level = 1.0
        self.canvas_offset_x = 0
        self.canvas_offset_y = 0
        self.dragging_canvas = False
        self.last_mouse_x = 0
        self.last_mouse_y = 0

        self.text_layers = []
        self.selected_layer = None
        self.current_font_path = ""
        self.current_color = "#000000"

        # Available pixel fonts (add your fonts to fonts/ folder)
        self.pixel_fonts = self.load_pixel_fonts()

        self.setup_ui()
        self.bind_events()

    def load_pixel_fonts(self):
        """Load pixel fonts from fonts folder"""
        fonts = {}
        fonts_dir = "fonts"

        # Create fonts directory if it doesn't exist
        if not os.path.exists(fonts_dir):
            os.makedirs(fonts_dir)
            print("Created 'fonts' folder - place your pixel font files (.ttf, .otf) here")

        # Load custom fonts from fonts folder
        if os.path.exists(fonts_dir):
            for file in os.listdir(fonts_dir):
                if file.lower().endswith(('.ttf', '.otf')):
                    font_path = os.path.join(fonts_dir, file)
                    font_name = os.path.splitext(file)[0]
                    fonts[font_name] = font_path

        # Add a default system font as fallback
        if not fonts:
            fonts["System Default"] = None

        return fonts

    def setup_ui(self):
        """Setup the user interface"""
        # Create main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel for controls
        left_panel = ttk.Frame(main_frame, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False)

        # Right panel for canvas
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.setup_left_panel(left_panel)
        self.setup_canvas(right_panel)

    def setup_left_panel(self, parent):
        """Setup the left control panel"""
        # File operations
        file_frame = ttk.LabelFrame(parent, text="File", padding=5)
        file_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(file_frame, text="Import Image", command=self.import_image).pack(fill=tk.X, pady=2)
        ttk.Button(file_frame, text="Export Image", command=self.export_image).pack(fill=tk.X, pady=2)

        # Font selection
        font_frame = ttk.LabelFrame(parent, text="Font Settings", padding=5)
        font_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(font_frame, text="Pixel Font:").pack(anchor=tk.W)
        self.font_var = tk.StringVar()
        font_names = list(self.pixel_fonts.keys())
        if font_names:
            self.font_var.set(font_names[0])
            self.current_font_path = self.pixel_fonts[font_names[0]]

        font_combo = ttk.Combobox(font_frame, textvariable=self.font_var, values=font_names, state="readonly")
        font_combo.pack(fill=tk.X, pady=2)
        font_combo.bind('<<ComboboxSelected>>', self.on_font_change)

        # Info label
        info_label = ttk.Label(font_frame, text="Fonts use their original pixel size",
                               font=('Arial', 8), foreground='gray')
        info_label.pack(anchor=tk.W, pady=(5, 0))

        # Color picker
        color_frame = ttk.Frame(font_frame)
        color_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(color_frame, text="Color:").pack(side=tk.LEFT)
        self.color_button = tk.Button(color_frame, bg=self.current_color, width=3, command=self.pick_color)
        self.color_button.pack(side=tk.RIGHT)

        # Text input
        text_frame = ttk.LabelFrame(parent, text="Text Input", padding=5)
        text_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(text_frame, text="Add Text Layer", command=self.add_text_layer).pack(fill=tk.X, pady=2)

        # Multi-line text
        ttk.Label(text_frame, text="Text content:").pack(anchor=tk.W, pady=(5, 0))
        self.text_area = tk.Text(text_frame, height=6, wrap=tk.WORD, font=('Courier', 9))
        text_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        self.text_area.configure(yscrollcommand=text_scrollbar.set)

        text_input_frame = ttk.Frame(text_frame)
        text_input_frame.pack(fill=tk.BOTH, expand=True)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_area.bind('<KeyRelease>', self.on_text_change)

        # Layer management
        layer_frame = ttk.LabelFrame(parent, text="Layers", padding=5)
        layer_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Layer listbox with scrollbar
        list_frame = ttk.Frame(layer_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.layer_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.layer_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.layer_listbox.yview)

        self.layer_listbox.bind('<<ListboxSelect>>', self.on_layer_select)

        # Layer controls
        layer_controls = ttk.Frame(layer_frame)
        layer_controls.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(layer_controls, text="Delete Layer", command=self.delete_layer).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(layer_controls, text="Duplicate", command=self.duplicate_layer).pack(side=tk.RIGHT)

        # Zoom controls
        zoom_frame = ttk.LabelFrame(parent, text="View", padding=5)
        zoom_frame.pack(fill=tk.X)

        zoom_controls = ttk.Frame(zoom_frame)
        zoom_controls.pack(fill=tk.X)

        ttk.Button(zoom_controls, text="Zoom In", command=self.zoom_in).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(zoom_controls, text="Zoom Out", command=self.zoom_out).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(zoom_controls, text="Fit", command=self.zoom_fit).pack(side=tk.RIGHT)

        self.zoom_label = ttk.Label(zoom_frame, text=f"Zoom: {int(self.zoom_level * 100)}%")
        self.zoom_label.pack(pady=(5, 0))

    def setup_canvas(self, parent):
        """Setup the main canvas"""
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        # Create canvas with scrollbars
        self.canvas = tk.Canvas(canvas_frame, bg='#2e2e2e', highlightthickness=0)

        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)

        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)

        # Grid layout for canvas and scrollbars
        self.canvas.grid(row=0, column=0, sticky='nsew')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')

        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)

    def bind_events(self):
        """Bind mouse and keyboard events"""
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        self.canvas.bind('<B1-Motion>', self.on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_canvas_release)
        self.canvas.bind('<Button-3>', self.on_canvas_right_click)  # Right click for canvas pan
        self.canvas.bind('<B3-Motion>', self.on_canvas_pan)
        self.canvas.bind('<MouseWheel>', self.on_mouse_wheel)
        self.canvas.bind('<Control-MouseWheel>', self.on_ctrl_mouse_wheel)  # Zoom with Ctrl+wheel

        # Keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.import_image())
        self.root.bind('<Control-s>', lambda e: self.export_image())
        self.root.bind('<Control-plus>', lambda e: self.zoom_in())
        self.root.bind('<Control-minus>', lambda e: self.zoom_out())
        self.root.bind('<Delete>', lambda e: self.delete_layer())

    def get_pixel_font_size(self, font_path):
        """Get the natural pixel size of a font by testing it"""
        if not font_path:
            return 12  # Default fallback

        try:
            # Test with a reasonable size to find the natural pixel dimensions
            test_font = ImageFont.truetype(font_path, 12)
            bbox = test_font.getbbox("A")
            height = bbox[3] - bbox[1]

            # For pixel fonts, try to find the intended pixel size
            # Most pixel fonts work best at specific sizes (8, 12, 16, etc.)
            pixel_sizes = [8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 24]

            for size in pixel_sizes:
                test_font = ImageFont.truetype(font_path, size)
                bbox = test_font.getbbox("A")
                if bbox[3] - bbox[1] == size or abs((bbox[3] - bbox[1]) - size) <= 1:
                    return size

            return 12  # Fallback
        except:
            return 12

    def create_text_image(self, text, font_path, color, threshold=200):
        """Create a sharp, pixel-perfect text image by removing semi-transparent pixels"""
        if not text.strip():
            return None

        try:
            font_size = self.get_pixel_font_size(font_path) if font_path else 12

            if font_path and os.path.exists(font_path):
                pil_font = ImageFont.truetype(font_path, font_size)
            else:
                pil_font = ImageFont.load_default()

            lines = text.split('\n')
            widths, heights = [], []

            for line in lines:
                bbox = pil_font.getbbox(line or "A")
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                widths.append(width)
                heights.append(height)

            img_width = max(widths) + 2
            img_height = sum(heights) + 2

            # Create transparent image and draw text
            img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            y = 1
            for i, line in enumerate(lines):
                draw.text((1, y), line, font=pil_font, fill=color)
                y += heights[i]

            # Convert to only solid pixels (remove anti-aliasing)
            pixels = img.load()
            for y in range(img.height):
                for x in range(img.width):
                    r, g, b, a = pixels[x, y]
                    if a < threshold:
                        pixels[x, y] = (0, 0, 0, 0)  # Fully transparent
                    else:
                        pixels[x, y] = (r, g, b, 255)  # Fully solid

            return img

        except Exception as e:
            print(f"[!] Error rendering pixel font: {e}")
            return None

    def import_image(self):
        """Import background image"""
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")]
        )

        if file_path:
            try:
                self.image = Image.open(file_path).convert('RGBA')
                self.update_canvas()
                self.zoom_fit()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")

    def export_image(self):
        """Export the final image with text layers"""
        if not self.image:
            messagebox.showwarning("Warning", "No image loaded to export")
            return

        file_path = filedialog.asksaveasfilename(
            title="Save Image",
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )

        if file_path:
            try:
                # Create a copy of the original image
                export_image = self.image.copy()

                # Render all text layers
                for layer in self.text_layers:
                    if layer.text.strip():
                        text_image = self.create_text_image(layer.text, layer.font_path, layer.color)
                        if text_image:
                            # Paste the text image at the correct position
                            export_image.paste(text_image, (layer.x, layer.y), text_image)

                export_image.save(file_path)
                messagebox.showinfo("Success", f"Image exported to {file_path}")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to export image: {str(e)}")

    def add_text_layer(self):
        """Add a new text layer"""
        if not self.image:
            messagebox.showwarning("Warning", "Please import an image first")
            return

        # Get text from text area
        text_content = self.text_area.get(1.0, tk.END).rstrip('\n')
        if not text_content.strip():
            text_content = "New Text"

        # Create new text layer at center of view
        center_x = max(0, int(self.canvas.canvasx(self.canvas.winfo_width() // 2) / self.zoom_level))
        center_y = max(0, int(self.canvas.canvasy(self.canvas.winfo_height() // 2) / self.zoom_level))

        layer = TextLayer(
            x=center_x,
            y=center_y,
            text=text_content,
            font_path=self.current_font_path,
            color=self.current_color
        )

        self.text_layers.append(layer)
        self.update_layer_list()
        self.update_canvas()

        # Select the new layer
        self.layer_listbox.selection_clear(0, tk.END)
        self.layer_listbox.selection_set(len(self.text_layers) - 1)
        self.on_layer_select(None)

    def update_layer_list(self):
        """Update the layer listbox"""
        self.layer_listbox.delete(0, tk.END)
        for i, layer in enumerate(self.text_layers):
            preview_text = layer.text.replace('\n', ' ')[:30]
            if len(layer.text) > 30:
                preview_text += "..."
            self.layer_listbox.insert(tk.END, f"Layer {i + 1}: {preview_text}")

    def on_layer_select(self, event):
        """Handle layer selection"""
        selection = self.layer_listbox.curselection()
        if selection:
            # Deselect all layers
            for layer in self.text_layers:
                layer.selected = False

            # Select the chosen layer
            layer_index = selection[0]
            self.selected_layer = self.text_layers[layer_index]
            self.selected_layer.selected = True

            # Update UI with layer properties
            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(1.0, self.selected_layer.text)

            # Update font selection
            for font_name, font_path in self.pixel_fonts.items():
                if font_path == self.selected_layer.font_path:
                    self.font_var.set(font_name)
                    break

            self.current_color = self.selected_layer.color
            self.color_button.config(bg=self.current_color)

            self.update_canvas()

    def delete_layer(self):
        """Delete selected layer"""
        if self.selected_layer:
            self.text_layers.remove(self.selected_layer)
            self.selected_layer = None
            self.update_layer_list()
            self.update_canvas()

    def duplicate_layer(self):
        """Duplicate selected layer"""
        if self.selected_layer:
            new_layer = TextLayer(
                x=self.selected_layer.x + 5,
                y=self.selected_layer.y + 5,
                text=self.selected_layer.text,
                font_path=self.selected_layer.font_path,
                color=self.selected_layer.color
            )
            self.text_layers.append(new_layer)
            self.update_layer_list()
            self.update_canvas()

    def on_font_change(self, event=None):
        """Handle font change"""
        font_name = self.font_var.get()
        self.current_font_path = self.pixel_fonts.get(font_name, None)
        if self.selected_layer:
            self.selected_layer.font_path = self.current_font_path
            self.update_canvas()

    def on_text_change(self, event=None):
        """Handle text change"""
        if self.selected_layer:
            self.selected_layer.text = self.text_area.get(1.0, tk.END).rstrip('\n')
            self.update_layer_list()
            self.update_canvas()

    def pick_color(self):
        """Open color picker"""
        color = colorchooser.askcolor(initialcolor=self.current_color)
        if color[1]:  # If user didn't cancel
            self.current_color = color[1]
            self.color_button.config(bg=self.current_color)
            if self.selected_layer:
                self.selected_layer.color = self.current_color
                self.update_canvas()

    def update_canvas(self):
        """Update the canvas display"""
        self.canvas.delete("all")

        if not self.image:
            return

        # Create the display image with text layers rendered
        self.display_image = self.image.copy()

        # Render text layers onto the display image
        for layer in self.text_layers:
            if layer.text.strip():
                text_image = self.create_text_image(layer.text, layer.font_path, layer.color)
                if text_image:
                    self.display_image.paste(text_image, (layer.x, layer.y), text_image)

        # Scale image for display with pixel-perfect scaling
        scaled_width = int(self.display_image.width * self.zoom_level)
        scaled_height = int(self.display_image.height * self.zoom_level)

        # Use NEAREST resampling for pixel-perfect scaling
        scaled_image = self.display_image.resize((scaled_width, scaled_height), Image.NEAREST)
        self.image_tk = ImageTk.PhotoImage(scaled_image)

        # Draw image
        self.canvas_image = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image_tk)

        # Draw selection indicators
        for layer in self.text_layers:
            if layer.selected and layer.text.strip():
                self.draw_selection_indicator(layer)

        # Update scroll region
        self.canvas.configure(scrollregion=(0, 0, scaled_width, scaled_height))

    def draw_selection_indicator(self, layer):
        """Draw selection indicator for a layer"""
        text_image = self.create_text_image(layer.text, layer.font_path, layer.color)
        if text_image:
            x1 = layer.x * self.zoom_level
            y1 = layer.y * self.zoom_level
            x2 = x1 + text_image.width * self.zoom_level
            y2 = y1 + text_image.height * self.zoom_level

            self.canvas.create_rectangle(
                x1 - 2, y1 - 2, x2 + 2, y2 + 2,
                outline="#ff0000", width=2, dash=(5, 5)
            )

    def on_canvas_click(self, event):
        """Handle canvas click"""
        if not self.image:
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # Convert to image coordinates
        img_x = int(canvas_x / self.zoom_level)
        img_y = int(canvas_y / self.zoom_level)

        # Check if clicked on a text layer
        clicked_layer = None
        for layer in reversed(self.text_layers):  # Check from top to bottom
            if layer.text.strip():
                text_image = self.create_text_image(layer.text, layer.font_path, layer.color)
                if text_image:
                    if (layer.x <= img_x <= layer.x + text_image.width and
                            layer.y <= img_y <= layer.y + text_image.height):
                        clicked_layer = layer
                        break

        if clicked_layer:
            # Select layer
            for layer in self.text_layers:
                layer.selected = False
            clicked_layer.selected = True
            self.selected_layer = clicked_layer

            # Update listbox selection
            layer_index = self.text_layers.index(clicked_layer)
            self.layer_listbox.selection_clear(0, tk.END)
            self.layer_listbox.selection_set(layer_index)
            self.on_layer_select(None)

            # Start dragging
            clicked_layer.dragging = True
            clicked_layer.drag_start_x = img_x - clicked_layer.x
            clicked_layer.drag_start_y = img_y - clicked_layer.y
        else:
            # Deselect all layers
            for layer in self.text_layers:
                layer.selected = False
            self.selected_layer = None
            self.layer_listbox.selection_clear(0, tk.END)

            # Start canvas panning
            self.dragging_canvas = True
            self.last_mouse_x = event.x
            self.last_mouse_y = event.y

        self.update_canvas()

    def on_canvas_drag(self, event):
        """Handle canvas drag"""
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # Check if dragging a text layer
        if self.selected_layer and self.selected_layer.dragging:
            img_x = int(canvas_x / self.zoom_level)
            img_y = int(canvas_y / self.zoom_level)

            self.selected_layer.x = max(0, img_x - self.selected_layer.drag_start_x)
            self.selected_layer.y = max(0, img_y - self.selected_layer.drag_start_y)
            self.update_canvas()
        elif self.dragging_canvas:
            # Pan canvas
            dx = event.x - self.last_mouse_x
            dy = event.y - self.last_mouse_y
            self.canvas.scan_dragto(dx, dy, gain=1)
            self.last_mouse_x = event.x
            self.last_mouse_y = event.y

    def on_canvas_release(self, event):
        """Handle canvas release"""
        if self.selected_layer:
            self.selected_layer.dragging = False
        self.dragging_canvas = False

    def on_canvas_right_click(self, event):
        """Handle right click for panning"""
        self.dragging_canvas = True
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

    def on_canvas_pan(self, event):
        """Handle canvas panning with right mouse"""
        if self.dragging_canvas:
            dx = event.x - self.last_mouse_x
            dy = event.y - self.last_mouse_y
            self.canvas.scan_dragto(dx, dy, gain=1)
            self.last_mouse_x = event.x
            self.last_mouse_y = event.y

    def on_mouse_wheel(self, event):
        """Handle mouse wheel for scrolling"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_ctrl_mouse_wheel(self, event):
        """Handle Ctrl+mouse wheel for zooming"""
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def zoom_in(self):
        """Zoom in"""
        self.zoom_level = min(self.zoom_level * 2.0, 32.0)  # Use 2x scaling for pixel-perfect zoom
        self.update_canvas()
        self.zoom_label.config(text=f"Zoom: {int(self.zoom_level * 100)}%")

    def zoom_out(self):
        """Zoom out"""
        self.zoom_level = max(self.zoom_level / 2.0, 0.125)  # Use 2x scaling for pixel-perfect zoom
        self.update_canvas()
        self.zoom_label.config(text=f"Zoom: {int(self.zoom_level * 100)}%")

    def zoom_fit(self):
        """Fit image to canvas"""
        if not self.image:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width > 1 and canvas_height > 1:
            zoom_x = canvas_width / self.image.width
            zoom_y = canvas_height / self.image.height

            # Find the nearest power of 2 for pixel-perfect scaling
            target_zoom = min(zoom_x, zoom_y) * 0.9
            powers_of_2 = [0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0]
            self.zoom_level = min(powers_of_2, key=lambda x: abs(x - target_zoom))

            self.update_canvas()
            self.zoom_label.config(text=f"Zoom: {int(self.zoom_level * 100)}%")


def main():
    root = tk.Tk()
    app = PixelTextEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()