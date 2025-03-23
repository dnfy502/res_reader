import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from PIL import Image, ImageTk, ImageDraw, ImageDraw
import threading

# Fix for PyMuPDF import - use explicit import to avoid module conflict
# try:
#     import PyMuPDF as fitz
# except ImportError:
try:
    # Alternative import - full path
    import pymupdf as fitz
except ImportError:
    print("Error: PyMuPDF library not found.")
    print("Please install it using: pip install PyMuPDF")
    sys.exit(1)

class PDFViewer:
    def __init__(self, root, pdf_path=None):
        self.root = root
        self.root.title("Research Paper Viewer")
        self.root.geometry("1000x900")  # Increased width to accommodate the notes panel
        
        # PDF document and current page
        self.doc = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_level = 1.0
        self.page_spacing = 20  # Space between different page segments in pixels
        # Text selection variables
        self.selected_text = ""
        self.selection_start = None
        self.selection_end = None
        self.text_instances = []  # Will store text block positions
        self.highlighted_areas = []  # Will store canvas rectangles for highlights
        
        # Add multi-selection variables
        self.is_appending = False  # Track if we're appending to selection (Ctrl pressed)
        self.previous_selections = []  # Store previous selections for appending
        
        # Variables for efficient continuous scrolling
        self.visible_page_range = 3  # Number of pages to keep in memory (current + adjacent pages)
        self.page_positions = []     # Store y-positions of each page
        self.page_heights = []       # Store heights of each page
        self.current_visible_pages = set()  # Currently rendered pages
        self.previously_visible_pages = set()  # Pages that were visible in the last render
        self.last_scroll_pos = 0.0   # Last scroll position for detection of scroll direction
        self.is_rendering = False    # Flag to prevent multiple simultaneous renders
        
        # Frame for controls
        self.control_frame = tk.Frame(root)
        self.control_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Remove Previous/Next buttons and replace with a page slider
        self.page_slider = ttk.Scale(
            self.control_frame, 
            from_=1, 
            to=1,  # Will be updated when PDF is loaded
            orient=tk.HORIZONTAL,
            command=self.on_page_slider_change
        )
        self.page_slider.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        self.page_label = tk.Label(self.control_frame, text="Page: 0/0")
        self.page_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Zoom buttons
        self.zoom_in_btn = tk.Button(self.control_frame, text="Zoom In", command=self.zoom_in)
        self.zoom_in_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        self.zoom_out_btn = tk.Button(self.control_frame, text="Zoom Out", command=self.zoom_out)
        self.zoom_out_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Open button
        self.open_btn = tk.Button(self.control_frame, text="Open PDF", command=self.open_pdf)
        self.open_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Add text selection indicator and copy button
        self.selection_label = tk.Label(self.control_frame, text="Selected: None", anchor=tk.W, width=30)
        self.selection_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.copy_btn = tk.Button(self.control_frame, text="Copy", command=self.copy_selected_text)
        self.copy_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Main content area - split into PDF view and notes panel using PanedWindow
        self.content_frame = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Canvas frame for PDF display
        self.canvas_frame = tk.Frame(self.content_frame)
        
        # Notes panel
        self.notes_frame = tk.Frame(self.content_frame, bg="#f0f0f0", relief=tk.GROOVE, bd=2)
        
        # Add both frames to the paned window
        self.content_frame.add(self.canvas_frame, weight=70)  # Default 70% of space
        self.content_frame.add(self.notes_frame, weight=30)   # Default 30% of space
        
        # Label for the notes panel
        notes_label = tk.Label(self.notes_frame, text="Selected Text", font=("Arial", 10, "bold"), bg="#f0f0f0")
        notes_label.pack(side=tk.TOP, pady=(10, 5), anchor=tk.W, padx=5)
        
        # Text display for selected text
        self.text_display = scrolledtext.ScrolledText(self.notes_frame, height=10, wrap=tk.WORD, font=("Arial", 9))
        self.text_display.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.text_display.config(state=tk.DISABLED)  # Make it read-only initially
        
        # Label for the notes input
        notes_input_label = tk.Label(self.notes_frame, text="Notes", font=("Arial", 10, "bold"), bg="#f0f0f0")
        notes_input_label.pack(side=tk.TOP, pady=(10, 5), anchor=tk.W, padx=5)
        
        # Text input for notes
        self.notes_input = scrolledtext.ScrolledText(self.notes_frame, height=10, wrap=tk.WORD, font=("Arial", 9))
        self.notes_input.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="gray")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        self.scrollbar = tk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Bind mouse events for text selection
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        
        # Track Ctrl key state for multi-selection
        self.root.bind("<KeyPress-Control_L>", self.ctrl_pressed)
        self.root.bind("<KeyPress-Control_R>", self.ctrl_pressed)
        self.root.bind("<KeyRelease-Control_L>", self.ctrl_released)
        self.root.bind("<KeyRelease-Control_R>", self.ctrl_released)
        
        # Bind trackpad/mouse wheel for zooming
        self.canvas.bind("<Control-MouseWheel>", self.on_mousewheel_zoom)  # Windows/Linux
        self.canvas.bind("<Control-Button-4>", self.on_mousewheel_zoom)    # Linux
        self.canvas.bind("<Control-Button-5>", self.on_mousewheel_zoom)    # Linux
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())         # Keyboard +
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())       # Keyboard -
        
        # Add mousewheel scrolling without Control key
        self.canvas.bind("<MouseWheel>", self.on_mousewheel_scroll)  # Windows/Linux
        self.canvas.bind("<Button-4>", self.on_mousewheel_scroll)    # Linux
        self.canvas.bind("<Button-5>", self.on_mousewheel_scroll)    # Linux
        
        # Bind for panning with middle mouse button
        self.canvas.bind("<ButtonPress-2>", self.scroll_start)
        self.canvas.bind("<B2-Motion>", self.scroll_move)
        
        # Load PDF if provided
        if pdf_path:
            self.load_pdf(pdf_path)

    def load_pdf(self, pdf_path):
        """Load a PDF file and display the first page"""
        try:
            self.doc = fitz.open(pdf_path)
            self.total_pages = len(self.doc)
            self.current_page = 0
            self.root.title(f"Research Paper Viewer - {pdf_path}")
            
            # Reset page tracking variables
            self.page_positions = []
            self.page_heights = []
            self.current_visible_pages = set()
            
            # Update slider range
            self.page_slider.configure(to=self.total_pages)
            self.page_slider.set(1)  # Set to first page
            
            # Pre-calculate page heights at current zoom level
            self.precalculate_page_heights()
            
            self.update_page_label()
            self.render_page()
        except Exception as e:
            print(f"Error opening PDF: {e}")
            messagebox.showerror("Error", f"Failed to open PDF: {e}")
    
    def open_pdf(self):
        """Open file dialog to select a PDF file"""
        pdf_path = filedialog.askopenfilename(
            title="Select PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if pdf_path:
            self.load_pdf(pdf_path)
    
    def precalculate_page_heights(self):
        """Pre-calculate heights of all pages at current zoom level"""
        if not self.doc:
            return
            
        self.page_heights = []
        self.page_positions = [0]  # First page starts at position 0
        
        total_height = 0
        
        # Calculate heights and positions for each page without actually rendering
        for page_num in range(self.total_pages):
            page = self.doc[page_num]
            
            # Get page dimensions and calculate height based on aspect ratio
            page_rect = page.rect
            width = page_rect.width * self.zoom_level
            height = page_rect.height * self.zoom_level
            
            self.page_heights.append(height)
            
            # Calculate position of next page
            total_height += height + self.page_spacing
            if page_num < self.total_pages - 1:
                self.page_positions.append(total_height)
    
    def render_page(self):
        """Render visible pages based on current scroll position"""
        if not self.doc:
            return
            
        # Prevent multiple simultaneous renders
        if self.is_rendering:
            return
            
        self.is_rendering = True
        
        # Clear canvas and reset text selection if not appending
        self.canvas.delete("all")
        self.text_instances = []
        if not self.is_appending:
            self.selected_text = ""
            self.previous_selections = []
            self.update_selection_label()
            self.update_text_display()
        
        # Determine which pages should be visible
        self.update_visible_pages()
        
        # Get the zoom matrix
        zoom_matrix = fitz.Matrix(self.zoom_level, self.zoom_level)
        
        # Calculate total height needed for all pages
        if not self.page_heights:  # If heights haven't been calculated yet
            self.precalculate_page_heights()
            
        total_height = self.page_positions[-1] + self.page_heights[-1] if self.page_heights else 0
        
        # Get visible region
        visible_top = self.canvas.canvasy(0)
        visible_bottom = visible_top + self.canvas.winfo_height()
        
        # Create placeholders for all pages
        max_width = 0
        for page_num in range(self.total_pages):
            page = self.doc[page_num]
            page_rect = page.rect
            width = page_rect.width * self.zoom_level
            max_width = max(max_width, width)
            
            # Create page boundaries for all pages that are part of the document
            y_offset = self.page_positions[page_num]
            height = self.page_heights[page_num]
            
            # Create a white rectangle for ALL pages in the document
            self.canvas.create_rectangle(
                0, y_offset, max_width, y_offset + height,
                fill="white", outline="#CCCCCC"
            )
            
            # Add page number as text to ALL pages
            self.canvas.create_text(
                10, y_offset + 10, 
                text=f"Page {page_num + 1}", 
                fill="#888888", 
                anchor="nw"
            )
            
            # Draw a separator line after each page (except the last one)
            if page_num < self.total_pages - 1:
                separator_y = y_offset + height + self.page_spacing // 2
                self.canvas.create_line(
                    0, separator_y, max_width, separator_y,
                    fill="#CCCCCC", width=2
                )
        
        # Set scrollregion to the size of the entire document
        self.canvas.config(scrollregion=(0, 0, max_width, total_height))
        
        # Define the pages to render (both visible and the closest 3)
        pages_to_render = self.current_visible_pages
        
        # Prioritize rendering order:
        # 1. Current page
        # 2. One page before and one page after current
        # 3. Other visible pages
        render_order = sorted(pages_to_render, key=lambda x: abs(x - self.current_page))
        
        # Render visible pages and closest 3 pages regardless of visibility
        for page_num in render_order:
            # Check if we already have this page rendered and cached
            if hasattr(self, 'photo_images') and page_num in self.photo_images:
                # If already cached, just display it on the canvas
                y_offset = self.page_positions[page_num]
                self.canvas.create_image(0, y_offset, anchor=tk.NW, image=self.photo_images[page_num])
                
                # If the page has text blocks already extracted, add them
                if hasattr(self, 'page_text_blocks') and page_num in self.page_text_blocks:
                    for text_block in self.page_text_blocks[page_num]:
                        self.text_instances.append(text_block)
            else:
                # If not cached, render in background thread
                threading.Thread(
                    target=self.render_page_in_background,
                    args=(page_num, zoom_matrix),
                    daemon=True
                ).start()
        
        # Reset rendering flag after a short delay to prevent too frequent updates
        self.root.after(100, self.reset_rendering_flag)
    
    def reset_rendering_flag(self):
        """Reset the rendering flag to allow new renders"""
        self.is_rendering = False
    
    def render_page_in_background(self, page_num, zoom_matrix):
        """Render a single page in the background thread"""
        try:
            # Get page position
            y_offset = self.page_positions[page_num]
            
            # Render the page (we'll always render pages in visible_pages set)
            page = self.doc[page_num]
            
            # Render the page at the correct aspect ratio
            pix = page.get_pixmap(matrix=zoom_matrix)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Extract text information
            text_page = page.get_text("dict")
            text_blocks = []
            
            # Process text blocks
            if 'blocks' in text_page:
                for block in text_page['blocks']:
                    if 'lines' not in block:
                        continue
                        
                    for line in block['lines']:
                        if 'spans' not in line:
                            continue
                            
                        for span in line['spans']:
                            if 'text' not in span or not span['text'].strip():
                                continue
                            
                            # Get text and its rectangle coords
                            text = span['text']
                            bbox = span['bbox']
                            
                            # Apply zoom
                            x0, y0, x1, y1 = bbox
                            x0 *= self.zoom_level
                            y0 *= self.zoom_level
                            x1 *= self.zoom_level
                            y1 *= self.zoom_level
                            
                            # Adjust for page position
                            y0 += y_offset
                            y1 += y_offset
                            
                            # Store text with its position
                            text_blocks.append({
                                'text': text,
                                'bbox': (x0, y0, x1, y1)
                            })
            
            # Use tkinter's after method to safely update the UI from the main thread
            self.root.after(0, lambda: self.update_canvas_with_page(page_num, img, text_blocks, y_offset))
            
        except Exception as e:
            print(f"Error rendering page {page_num}: {e}")
    
    def update_canvas_with_page(self, page_num, img, text_blocks, y_offset):
        """Update the canvas with a rendered page (called from the main thread)"""
        # Only continue if the page is still part of visible pages
        if page_num not in self.current_visible_pages:
            return
            
        # Create a PhotoImage and keep a reference to prevent garbage collection
        if not hasattr(self, 'photo_images'):
            self.photo_images = {}
            
        # Store the image
        self.photo_images[page_num] = ImageTk.PhotoImage(image=img)
        
        # Create text blocks storage if it doesn't exist
        if not hasattr(self, 'page_text_blocks'):
            self.page_text_blocks = {}
            
        # Store text blocks for this page
        self.page_text_blocks[page_num] = text_blocks
        
        # Always display the page on the canvas (since it's in visible_pages)
        self.canvas.create_image(0, y_offset, anchor=tk.NW, image=self.photo_images[page_num])
        
        # Add text blocks to the text_instances list
        for text_block in text_blocks:
            self.text_instances.append(text_block)
    
    def update_visible_pages(self):
        """Determine which pages should be visible based on scroll position"""
        if not self.doc or not self.page_positions:
            return
            
        # Get current view position (what's visible in the canvas)
        view_top = self.canvas.canvasy(0)  # Top of current view
        view_height = self.canvas.winfo_height()
        view_bottom = view_top + view_height  # Bottom of current view
        
        # Find which page is at the center of the view
        center_y = view_top + (view_height / 2)
        center_page = self.find_page_at_position(center_y)
        
        # Update current page
        if center_page != self.current_page:
            self.current_page = center_page
            self.update_page_label()
            # Update slider without triggering the callback
            self.page_slider.set(self.current_page + 1)
        
        # Calculate range for visible pages based on what's actually in view
        visible_pages = set()
        for page_num in range(self.total_pages):
            y_offset = self.page_positions[page_num]
            height = self.page_heights[page_num]
            
            # Check if this page is visible or partially visible
            if not (y_offset > view_bottom or y_offset + height < view_top):
                visible_pages.add(page_num)
        
        # Always include the 3 closest pages centered on current_page
        closest_pages = set(range(
            max(0, self.current_page - 1),
            min(self.total_pages, self.current_page + 2)
        ))
        
        # Combine visible and closest pages for rendering
        new_visible_pages = visible_pages.union(closest_pages)
        
        # Only update if the visible pages have changed
        if new_visible_pages != self.current_visible_pages:
            # Store the current visible pages
            self.current_visible_pages = new_visible_pages
            
            # Identify pages that need to be unloaded
            if hasattr(self, 'photo_images'):
                keys_to_remove = [k for k in self.photo_images.keys() if k not in new_visible_pages]
                for k in keys_to_remove:
                    del self.photo_images[k]
    
    def find_page_at_position(self, y_position):
        """Find which page contains the given y-position"""
        if not self.page_positions:
            return 0
            
        # Binary search to find the page
        left = 0
        right = len(self.page_positions) - 1
        
        while left <= right:
            mid = (left + right) // 2
            
            # Check if position is on this page
            page_top = self.page_positions[mid]
            page_bottom = page_top + self.page_heights[mid]
            
            if page_top <= y_position < page_bottom:
                return mid
            elif y_position < page_top:
                right = mid - 1
            else:
                left = mid + 1
                
        # If not found directly, return the closest page
        return min(max(0, left), self.total_pages - 1)
    
    def on_page_slider_change(self, event):
        """Handle page slider change"""
        if not self.doc:
            return
            
        # Get page number from slider
        page_num = int(float(self.page_slider.get())) - 1
        
        # Scroll to that page
        self.scroll_to_page(page_num)
    
    def scroll_to_page(self, page_num):
        """Scroll to show the specified page"""
        if not self.doc or not self.page_positions or page_num < 0 or page_num >= self.total_pages:
            return
            
        # Calculate position to scroll to (the top of the page)
        y_pos = self.page_positions[page_num]
        
        # Get total height of document
        total_height = self.page_positions[-1] + self.page_heights[-1]
        
        # Scroll to position
        self.canvas.yview_moveto(y_pos / total_height)
        
        # Update current page
        self.current_page = page_num
        self.update_page_label()
        
        # Reset rendering flag
        self.is_rendering = False
        
        # Force a complete re-render to ensure all pages are displayed properly
        self.update_visible_pages()
        self.render_page()
    
    def ctrl_pressed(self, event):
        """Handle Ctrl key press for multi-selection"""
        self.is_appending = True
    
    def ctrl_released(self, event):
        """Handle Ctrl key release"""
        self.is_appending = False
    
    def on_mouse_down(self, event):
        """Handle mouse button press for text selection"""
        # Adjust coordinates for canvas scrolling
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # If not appending (Ctrl not pressed), clear previous selections
        if not self.is_appending:
            self.clear_highlights()
            self.previous_selections = []
            self.selected_text = ""
        else:
            # If appending, save current selection before starting a new one
            if self.selected_text:
                self.previous_selections.append(self.selected_text)
        
        self.selection_start = (canvas_x, canvas_y)
        self.selection_end = None
        self.update_selection_label()
    
    def on_mouse_drag(self, event):
        """Handle mouse drag for text selection"""
        if self.selection_start:
            # Adjust coordinates for canvas scrolling
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            self.selection_end = (canvas_x, canvas_y)
            self.update_selection()
    
    def on_mouse_up(self, event):
        """Handle mouse button release for text selection"""
        if self.selection_start:
            # Adjust coordinates for canvas scrolling
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            self.selection_end = (canvas_x, canvas_y)
            self.update_selection()
    
    def update_selection(self):
        """Update text selection based on mouse position"""
        if not self.selection_start or not self.selection_end:
            return
            
        # Create a selection rectangle
        x1, y1 = self.selection_start
        x2, y2 = self.selection_end
        
        # Make sure x1,y1 is the top-left and x2,y2 is the bottom-right
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        
        selection_rect = (x1, y1, x2, y2)
        selected_texts = []
        current_selection = ""
        
        # If we're not clearing previous selections, don't clear highlights
        if not self.is_appending:
            self.clear_highlights()
        
        # Check which text blocks intersect with the selection rectangle
        for text_obj in self.text_instances:
            text = text_obj['text']
            bbox = text_obj['bbox']
            
            # Check for intersection
            if self.rectangles_intersect(selection_rect, bbox):
                selected_texts.append(text)
                
                # Use different highlight colors for multi-selection
                highlight_color = "#FF7F50" # Default color
                outline_color = "#FF4500"   # Default outline
                
                if self.is_appending:
                    # Use a different color for appended selections
                    highlight_color = "#90EE90"  # Light green
                    outline_color = "#32CD32"    # Lime green
                
                # Highlight the selected text
                highlight = self.canvas.create_rectangle(
                    bbox[0], bbox[1], bbox[2], bbox[3],
                    fill=highlight_color, outline=outline_color, stipple="gray25"
                )
                self.highlighted_areas.append(highlight)
        
        # Join all selected text with spaces
        current_selection = " ".join(selected_texts)
        
        # If appending, combine current selection with previous selections
        if self.is_appending:
            combined_selections = self.previous_selections + [current_selection]
            self.selected_text = " ".join(filter(bool, combined_selections))
        else:
            self.selected_text = current_selection
            
        self.update_selection_label()
        self.update_text_display()
    
    def rectangles_intersect(self, rect1, rect2):
        """Check if two rectangles intersect"""
        x1_1, y1_1, x2_1, y2_1 = rect1
        x1_2, y1_2, x2_2, y2_2 = rect2
        
        # Check if one rectangle is on the left side of the other
        if x2_1 < x1_2 or x2_2 < x1_1:
            return False
            
        # Check if one rectangle is above the other
        if y2_1 < y1_2 or y2_2 < y1_1:
            return False
            
        return True
    
    def clear_highlights(self):
        """Clear all highlighted text areas"""
        for highlight in self.highlighted_areas:
            self.canvas.delete(highlight)
        self.highlighted_areas = []
    
    def update_selection_label(self):
        """Update the selection label with selected text info"""
        if not self.selected_text:
            self.selection_label.config(text="Selected: None")
        else:
            # Truncate long selections for display
            display_text = self.selected_text[:30] + "..." if len(self.selected_text) > 30 else self.selected_text
            self.selection_label.config(text=f"Selected: {display_text}")
    
    def update_text_display(self):
        """Update the text display in the notes panel with the selected text"""
        # Enable editing, clear the display, insert new text, then disable again
        self.text_display.config(state=tk.NORMAL)
        self.text_display.delete(1.0, tk.END)
        if self.selected_text:
            self.text_display.insert(tk.END, self.selected_text)
        self.text_display.config(state=tk.DISABLED)
    
    def copy_selected_text(self):
        """Copy selected text to clipboard"""
        if self.selected_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.selected_text)
            messagebox.showinfo("Copied", "Text copied to clipboard")
    
    def on_mousewheel_zoom(self, event):
        """Handle trackpad/mouse wheel for zooming with better performance"""
        old_zoom = self.zoom_level
        
        # Determine zoom direction based on event type and delta
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            self.zoom_level *= 1.1  # Zoom in
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            self.zoom_level *= 0.9  # Zoom out
            
        # Ensure reasonable zoom limits
        self.zoom_level = max(0.2, min(5.0, self.zoom_level))
        
        # Only recalculate if zoom actually changed
        if old_zoom != self.zoom_level:
            # Remember current page
            current_page = self.current_page
            
            # Clear photo image cache
            if hasattr(self, 'photo_images'):
                self.photo_images = {}
            
            # Recalculate page heights and positions
            self.precalculate_page_heights()
            
            # Re-render
            self.scroll_to_page(current_page)
            
        return "break"  # Prevent event propagation
    
    def on_mousewheel_scroll(self, event):
        """Handle mousewheel scrolling with dynamic page loading"""
        # Existing scroll code
        scroll_amount = 0
        
        # Handle different platforms
        if event.num == 4:
            scroll_amount = -1  # Scroll up (Linux)
        elif event.num == 5:
            scroll_amount = 1   # Scroll down (Linux)
        elif hasattr(event, 'delta'):
            # For Windows/macOS
            scroll_amount = -1 if event.delta > 0 else 1
        
        # Adjust scroll speed
        scroll_units = 2  # Increased for better scrolling speed
        self.canvas.yview_scroll(scroll_amount * scroll_units, "units")
        
        # Store current scroll position
        current_pos = self.canvas.yview()[0]  # Get top position as fraction
        
        # Check if we need to update page rendering
        if abs(current_pos - self.last_scroll_pos) > 0.03:  # Threshold to reduce frequency
            self.last_scroll_pos = current_pos
            
            # Cancel any pending updates to avoid redundant rendering
            if hasattr(self, 'after_id'):
                try:
                    self.root.after_cancel(self.after_id)
                except:
                    pass
                    
            # Schedule a new update
            self.after_id = self.root.after(50, self.delayed_render_update)
            
        return "break"  # Prevent event propagation
    
    def delayed_render_update(self):
        """Update visible pages and render with a slight delay to prevent too frequent updates"""
        self.update_visible_pages()
        self.render_page()
    
    def scroll_start(self, event):
        """Start scrolling with middle mouse button"""
        self.canvas.scan_mark(event.x, event.y)
    
    def scroll_move(self, event):
        """Move/pan canvas with middle mouse button"""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
    
    def prev_page(self):
        """Go to previous page - now handled by slider and scrolling"""
        if self.doc and self.current_page > 0:
            self.scroll_to_page(self.current_page - 1)
    
    def next_page(self):
        """Go to next page - now handled by slider and scrolling"""
        if self.doc and self.current_page < self.total_pages - 1:
            self.scroll_to_page(self.current_page + 1)
    
    def update_page_label(self):
        """Update the page counter label"""
        if self.doc:
            self.page_label.config(text=f"Page: {self.current_page + 1}/{self.total_pages}")
    
    def zoom_in(self):
        """Increase zoom level with better performance"""
        old_zoom = self.zoom_level
        self.zoom_level *= 1.25
        self.zoom_level = min(5.0, self.zoom_level)  # Lower maximum zoom for stability
        
        # Only recalculate if zoom actually changed
        if old_zoom != self.zoom_level:
            # Remember current page
            current_page = self.current_page
            
            # Reset rendering flag
            self.is_rendering = False
            
            # Clear photo image cache completely when zooming
            if hasattr(self, 'photo_images'):
                self.photo_images = {}
            
            # Recalculate page heights and positions
            self.precalculate_page_heights()
            
            # Re-render
            self.scroll_to_page(current_page)
    
    def zoom_out(self):
        """Decrease zoom level with better performance"""
        old_zoom = self.zoom_level
        self.zoom_level *= 0.8
        self.zoom_level = max(0.2, self.zoom_level)  # Higher minimum zoom for usability
        
        # Only recalculate if zoom actually changed
        if old_zoom != self.zoom_level:
            # Remember current page
            current_page = self.current_page
            
            # Reset rendering flag
            self.is_rendering = False
            
            # Clear photo image cache completely when zooming
            if hasattr(self, 'photo_images'):
                self.photo_images = {}
            
            # Recalculate page heights and positions
            self.precalculate_page_heights()
            
            # Re-render
            self.scroll_to_page(current_page)
    
    # Remove render_page_segment method as it's no longer needed
    def render_page_segment(self, page, zoom_matrix, segment='full'):
        """Legacy method - keeping as stub for compatibility"""
        page_rect = page.rect
        clip = page_rect
        pix = page.get_pixmap(matrix=zoom_matrix)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img, pix.height, []  # Return empty text blocks list

def main():
    root = tk.Tk()
    pdf_path = 'pdfs/2403.07721v7.pdf'
    
    # Check if a file path was provided as a command-line argument
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    
    app = PDFViewer(root, pdf_path)
    root.mainloop()

if __name__ == "__main__":
    main()
