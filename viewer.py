import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from PIL import Image, ImageTk, ImageDraw, ImageDraw
import threading

# Fix for PyMuPDF import - use explicit import to avoid module conflict
try:
    import PyMuPDF as fitz
except ImportError:
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
        # Text selection variables
        self.selected_text = ""
        self.selection_start = None
        self.selection_end = None
        self.text_instances = []  # Will store text block positions
        self.highlighted_areas = []  # Will store canvas rectangles for highlights
        
        # Frame for controls
        self.control_frame = tk.Frame(root)
        self.control_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Navigation buttons
        self.prev_btn = tk.Button(self.control_frame, text="Previous", command=self.prev_page)
        self.prev_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.next_btn = tk.Button(self.control_frame, text="Next", command=self.next_page)
        self.next_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
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
            self.update_page_label()
            self.render_page()
        except Exception as e:
            print(f"Error opening PDF: {e}")
    
    def open_pdf(self):
        """Open file dialog to select a PDF file"""
        pdf_path = filedialog.askopenfilename(
            title="Select PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if pdf_path:
            self.load_pdf(pdf_path)
    
    def render_page(self):
        """Render the current page with text information for selection"""
        if not self.doc:
            return
        
        # Clear canvas and reset text selection
        self.canvas.delete("all")
        self.text_instances = []
        self.selected_text = ""
        self.update_selection_label()
        self.update_text_display()
        
        # Get the current page
        current_page = self.doc[self.current_page]
        
        # Create a blank image to merge content onto
        merged_image = None
        merged_height = 0
        y_offset = 0
        
        # Get the zoom matrix
        zoom_matrix = fitz.Matrix(self.zoom_level, self.zoom_level)
        
        # Load the bottom part of the previous page if it exists
        if self.current_page > 0:
            prev_page = self.doc[self.current_page - 1]
            prev_image, prev_height, prev_texts = self.render_page_segment(prev_page, zoom_matrix, 'bottom')
            if prev_image:
                merged_image = prev_image
                merged_height = prev_height
                y_offset = prev_height + self.page_spacing  # Add spacing after prev page segment
                
                # Add text blocks from previous page (with adjusted y-coordinates)
                for text_obj in prev_texts:
                    self.text_instances.append(text_obj)
        
        # Load the current page
        current_image, current_height, current_texts = self.render_page_segment(current_page, zoom_matrix, 'full')
        
        # If we don't have an image yet (no previous page), start with current page
        if merged_image is None:
            merged_image = current_image
            merged_height = current_height
        else:
            # Create a new taller image with spacing and paste current page below previous page's bottom half
            new_height = merged_height + self.page_spacing + current_height
            new_image = Image.new("RGB", (current_image.width, new_height), "white")
            new_image.paste(merged_image, (0, 0))
            
            # Draw a separator line
            separator_y = merged_height + self.page_spacing // 2
            draw = ImageDraw.Draw(new_image)
            draw.line([(0, separator_y), (current_image.width, separator_y)], fill="#CCCCCC", width=2)
            
            new_image.paste(current_image, (0, y_offset))
            merged_image = new_image
            merged_height = new_height
        
        # Adjust y-coordinates for text blocks from current page
        for text_obj in current_texts:
            text = text_obj['text']
            x0, y0, x1, y1 = text_obj['bbox']
            self.text_instances.append({
                'text': text,
                'bbox': (x0, y0 + y_offset, x1, y1 + y_offset)
            })
        
        # Set new y_offset to include current page and spacing
        y_offset = merged_height + self.page_spacing
        
        # Load the top part of the next page if it exists
        if self.current_page < self.total_pages - 1:
            next_page = self.doc[self.current_page + 1]
            next_image, next_height, next_texts = self.render_page_segment(next_page, zoom_matrix, 'top')
            if next_image:
                # Create a new taller image with spacing and paste next page's top half below
                new_height = merged_height + self.page_spacing + next_height
                new_image = Image.new("RGB", (next_image.width, new_height), "white")
                new_image.paste(merged_image, (0, 0))
                
                # Draw a separator line
                separator_y = merged_height + self.page_spacing // 2
                draw = ImageDraw.Draw(new_image)
                draw.line([(0, separator_y), (next_image.width, separator_y)], fill="#CCCCCC", width=2)
                
                new_image.paste(next_image, (0, y_offset))
                merged_image = new_image
                
                # Add text blocks from next page (with adjusted y-coordinates)
                for text_obj in next_texts:
                    text = text_obj['text']
                    x0, y0, x1, y1 = text_obj['bbox']
                    self.text_instances.append({
                        'text': text,
                        'bbox': (x0, y0 + y_offset, x1, y1 + y_offset)
                    })
        
        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(image=merged_image)
        
        # Display image
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Set scrollregion to the size of the merged image
        self.canvas.config(scrollregion=(0, 0, merged_image.width, merged_image.height))
    
    def render_page_segment(self, page, zoom_matrix, segment='full'):
        """Render a segment of a page and return the image and text blocks
        
        Args:
            page: The page to render
            zoom_matrix: The zoom matrix to apply
            segment: 'full', 'top', or 'bottom'
            
        Returns:
            tuple: (PIL Image, height of image, list of text blocks)
        """
        # Get page dimensions
        page_rect = page.rect
        
        # Create a clip rectangle based on segment type
        if segment == 'top':
            # Top half of the page
            clip = fitz.Rect(page_rect.x0, page_rect.y0, 
                            page_rect.x1, page_rect.y0 + page_rect.height/2)
        elif segment == 'bottom':
            # Bottom half of the page
            clip = fitz.Rect(page_rect.x0, page_rect.y0 + page_rect.height/2, 
                            page_rect.x1, page_rect.y1)
        else:
            # Full page
            clip = page_rect
            
        # Get the pixmap with the clip rectangle
        pix = page.get_pixmap(matrix=zoom_matrix, clip=clip)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Extract text blocks with their positions
        text_page = page.get_text("dict", clip=clip)
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
                        
                        # Apply zoom to the coordinates
                        x0, y0, x1, y1 = bbox
                        
                        # Adjust coordinates to be relative to the clip rectangle
                        if segment == 'bottom':
                            y0 -= page_rect.height/2
                            y1 -= page_rect.height/2
                        
                        # Apply zoom
                        x0 *= self.zoom_level
                        y0 *= self.zoom_level
                        x1 *= self.zoom_level
                        y1 *= self.zoom_level
                        
                        # Store text with its position
                        text_blocks.append({
                            'text': text,
                            'bbox': (x0, y0, x1, y1)
                        })
                        
        return img, pix.height, text_blocks
    
    def process_text_blocks(self, text_page, zoom_matrix):
        """Process and store text block information for selection"""
        if 'blocks' not in text_page:
            return
            
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
                    
                    # Apply zoom to the coordinates
                    x0, y0, x1, y1 = bbox
                    x0 *= self.zoom_level
                    y0 *= self.zoom_level
                    x1 *= self.zoom_level
                    y1 *= self.zoom_level
                    
                    # Store text with its position
                    self.text_instances.append({
                        'text': text,
                        'bbox': (x0, y0, x1, y1)
                    })
    
    def on_mouse_down(self, event):
        """Handle mouse button press for text selection"""
        self.clear_highlights()
        # Adjust coordinates for canvas scrolling
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        self.selection_start = (canvas_x, canvas_y)
        self.selection_end = None
        self.selected_text = ""
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
            
        self.clear_highlights()
        
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
        
        # Check which text blocks intersect with the selection rectangle
        for text_obj in self.text_instances:
            text = text_obj['text']
            bbox = text_obj['bbox']
            
            # Check for intersection
            if self.rectangles_intersect(selection_rect, bbox):
                selected_texts.append(text)
                # Highlight the selected text with a more visible color
                highlight = self.canvas.create_rectangle(
                    bbox[0], bbox[1], bbox[2], bbox[3],
                    fill="#FF7F50", outline="#FF4500", stipple="gray25"  # Bright coral color with orange-red outline
                )
                self.highlighted_areas.append(highlight)
        
        # Join all selected text with spaces
        self.selected_text = " ".join(selected_texts)
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
        """Handle trackpad/mouse wheel for zooming"""
        # Determine zoom direction based on event type and delta
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            self.zoom_level *= 1.1  # Zoom in
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            self.zoom_level *= 0.9  # Zoom out
            
        # Ensure reasonable zoom limits
        self.zoom_level = max(0.1, min(10.0, self.zoom_level))
        
        # Re-render the page with the new zoom level
        self.render_page()
        return "break"  # Prevent event propagation
    
    def on_mousewheel_scroll(self, event):
        """Handle mousewheel scrolling"""
        # Determine scroll direction and amount
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
        return "break"  # Prevent event propagation
    
    def scroll_start(self, event):
        """Start scrolling with middle mouse button"""
        self.canvas.scan_mark(event.x, event.y)
    
    def scroll_move(self, event):
        """Move/pan canvas with middle mouse button"""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
    
    def prev_page(self):
        """Go to previous page"""
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.update_page_label()
            self.render_page()
    
    def next_page(self):
        """Go to next page"""
        if self.doc and self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_page_label()
            self.render_page()
    
    def update_page_label(self):
        """Update the page counter label"""
        if self.doc:
            self.page_label.config(text=f"Page: {self.current_page + 1}/{self.total_pages}")
    
    def zoom_in(self):
        """Increase zoom level"""
        self.zoom_level *= 1.25
        self.render_page()
    
    def zoom_out(self):
        """Decrease zoom level"""
        self.zoom_level *= 0.8
        self.render_page()

def main():
    root = tk.Tk()
    pdf_path = 'pdfs/Dataset_Second.pdf'
    
    # Check if a file path was provided as a command-line argument
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    
    app = PDFViewer(root, pdf_path)
    root.mainloop()

if __name__ == "__main__":
    main()
