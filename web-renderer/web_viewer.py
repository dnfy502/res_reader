import os
from flask import Flask, send_from_directory, render_template, request, jsonify

app = Flask(__name__)

# Create templates and static directories if they don't exist
os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)

@app.route('/')
def index():
    return render_template('viewer.html')

@app.route('/pdf/<path:filename>')
def serve_pdf(filename):
    pdf_dir = os.path.join(os.path.dirname(__file__), 'pdfs')
    return send_from_directory(pdf_dir, filename)

@app.route('/api/pdf-list')
def list_pdfs():
    pdf_dir = os.path.join(os.path.dirname(__file__), 'pdfs')
    if os.path.exists(pdf_dir):
        files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
        return jsonify(files)
    return jsonify([])

@app.route('/api/selection', methods=['POST'])
def handle_selection():
    data = request.json
    selected_text = data.get('text', '')
    print(f"Selected text: {selected_text}")
    return jsonify({"status": "success"})

if __name__ == '__main__':
    # Create the pdfs directory if it doesn't exist
    os.makedirs(os.path.join(os.path.dirname(__file__), 'pdfs'), exist_ok=True)
    print("Server started at http://localhost:5000")
    print("Please place your PDF files in the 'pdfs' directory")
    app.run(debug=True)
