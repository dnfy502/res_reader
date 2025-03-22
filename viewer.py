import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
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
        self.root.geometry("800x900")
        
        # PDF document and current page
        self.doc = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_level = 1.0
        
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
        
        # Canvas for PDF display
        self.canvas_frame = tk.Frame(root)
        self.canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
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
        
        # Get the page
        page = self.doc[self.current_page]
        
        # Get the zoom matrix
        zoom_matrix = fitz.Matrix(self.zoom_level, self.zoom_level)
        
        # Get the pixmap
        pix = page.get_pixmap(matrix=zoom_matrix)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(image=img)
        
        # Display image
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Extract text blocks with their positions
        text_page = page.get_text("dict")
        self.process_text_blocks(text_page, zoom_matrix)
        
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))
    
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
        self.selection_start = (event.x, event.y)
        self.selection_end = None
        self.selected_text = ""
        self.update_selection_label()
    
    def on_mouse_drag(self, event):
        """Handle mouse drag for text selection"""
        if self.selection_start:
            self.selection_end = (event.x, event.y)
            self.update_selection()
    
    def on_mouse_up(self, event):
        """Handle mouse button release for text selection"""
        if self.selection_start:
            self.selection_end = (event.x, event.y)
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
                # Highlight the selected text
                highlight = self.canvas.create_rectangle(
                    bbox[0], bbox[1], bbox[2], bbox[3],
                    fill="lightyellow", outline="", stipple="gray12"
                )
                self.highlighted_areas.append(highlight)
        
        # Join all selected text with spaces
        self.selected_text = " ".join(selected_texts)
        self.update_selection_label()
    
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
    
    def on_mousewheel_scroll(self, event):
        """Handle mousewheel scrolling"""
        # Determine scroll direction and amount
        if event.num == 4 or (hasattr(event, 'delta') and event.delta > 0):
            scroll_amount = -1  # Scroll up
        elif event.num == 5 or (hasattr(event, 'delta') and event.delta < 0):
            scroll_amount = 1   # Scroll down
        else:
            return
            
        # Adjust scroll speed based on platform
        if hasattr(event, 'delta'):
            # For Windows, scale the scroll amount
            scroll_amount = int(scroll_amount * abs(event.delta) / 120)
        
        # Scroll the canvas with appropriate units
        scroll_units = 30  # Adjust this value for faster/slower scrolling
        self.canvas.yview_scroll(scroll_amount * scroll_units, "units")
    
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
    pdf_path = 'Dataset_Second.pdf'
    
    # Check if a file path was provided as a command-line argument
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    
    app = PDFViewer(root, pdf_path)
    root.mainloop()

if __name__ == "__main__":
    main()
