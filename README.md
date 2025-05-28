# Research Reader

A powerful research paper analysis and visualization tool that combines PDF viewing capabilities with advanced AI-powered question answering using Google's Gemini model.

## Features

- **Interactive PDF Viewer**
  - Smooth scrolling and zooming
  - Text selection and highlighting
  - Multi-page navigation
  - Split-pane interface with notes panel
  - Efficient memory management for large documents

- **AI-Powered Analysis**
  - RAG (Retrieval-Augmented Generation) system using Google's Gemini model
  - Intelligent question answering based on paper content
  - Context-aware responses
  - Support for multiple PDF documents

- **Advanced Text Processing**
  - Efficient text extraction from PDFs
  - Smart text chunking for better context understanding
  - Vector-based semantic search
  - High-quality text embedding generation

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/research-reader.git
cd research-reader
```

2. Create and activate a virtual environment:
```bash
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your Google Gemini API key:
   - Get an API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Set it as an environment variable or provide it when running the application

## Usage

### PDF Viewer

Run the viewer application:
```bash
python viewer.py
```

The viewer provides the following features:
- Open PDF files using the "Open PDF" button
- Navigate pages using the slider or mouse wheel
- Zoom in/out using Ctrl + mouse wheel or the zoom buttons
- Select text by clicking and dragging
- Add notes in the side panel
- Copy selected text to clipboard

### RAG System

Run the RAG system:
```bash
python rag.py --api_key YOUR_API_KEY --pdf path/to/your/paper.pdf
```

Or use it interactively:
```bash
python rag.py --api_key YOUR_API_KEY
```

Interactive commands:
- `load <pdf_path>`: Load a new PDF document
- Ask questions about the loaded document
- Type 'quit' or 'exit' to end the session

## Project Structure

- `viewer.py`: Main PDF viewer application
- `rag.py`: RAG system implementation
- `custom_pipeline.py`: Custom text processing pipeline
- `requirements.txt`: Project dependencies
- `pdfs/`: Directory for storing PDF files

## Dependencies

- **Core Dependencies**
  - langchain: Framework for LLM applications
  - google-generativeai: Google's Gemini AI API
  - faiss-cpu: Vector similarity search
  - PyPDF2: PDF processing
  - PyMuPDF: Advanced PDF rendering
  - Pillow: Image processing
  - torch: Deep learning framework
  - diffusers: Stable Diffusion models
  - transformers: Hugging Face transformers

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Gemini AI for providing the language model
- Hugging Face for the transformers library
- The open-source community for various tools and libraries used in this project 