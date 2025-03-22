import os
from flask import Flask, send_from_directory, render_template, request, jsonify
import glob

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('viewer.html')

@app.route('/pdf/<path:filename>')
def serve_pdf(filename):
    pdf_dir = os.path.join(os.path.dirname(__file__), 'pdfs')
    return send_from_directory(pdf_dir, filename)

@app.route('/api/pdf-list')
def pdf_list():
    pdf_dir = os.path.join(os.path.dirname(__file__), 'pdfs')
    pdf_files = [os.path.basename(f) for f in glob.glob(os.path.join(pdf_dir, '*.pdf'))]
    return jsonify(pdf_files)

@app.route('/api/selection', methods=['POST'])
def handle_selection():
    data = request.json
    selected_text = data.get('text', '')
    print(f"Selected text: {selected_text}")
    return jsonify({"status": "success"})

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), 'pdfs'), exist_ok=True)
    
    print("\n=== Research PDF Viewer ===")
    print("Server started at http://localhost:5000")
    print(f"Please place your PDF files in the '{os.path.abspath(os.path.join(os.path.dirname(__file__), 'pdfs'))}' directory")
    app.run(debug=True)
