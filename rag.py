import os
import tempfile
from typing import List, Dict, Any

# PDF processing
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Vector store
import numpy as np
# Replace the incorrect import
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

# LLM 
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

class RAGSystem:
    def __init__(self, api_key: str):
        """Initialize the RAG system with the Google Gemini API key."""
        self.api_key = api_key
        os.environ["GOOGLE_API_KEY"] = api_key
        genai.configure(api_key=api_key)
        
        # Initialize the embedding model
        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key,
        )
        
        # Initialize the Gemini model for chat
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=api_key,
            temperature=0.2,
        )
        
        # Initialize text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        self.vector_store = None
        self.pdf_text = ""
        
    def load_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file."""
        print(f"Loading PDF from {pdf_path}...")
        pdf_reader = PdfReader(pdf_path)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        self.pdf_text = text
        print(f"Extracted {len(text)} characters from PDF.")
        return text
    
    def process_pdf(self, pdf_path: str) -> None:
        """Process a PDF document and create a vector store from its content."""
        # Extract text from PDF
        text = self.load_pdf(pdf_path)
        
        # Split text into chunks
        print("Splitting text into chunks...")
        chunks = self.text_splitter.split_text(text)
        print(f"Created {len(chunks)} text chunks.")
        
        # Create vector store
        print("Creating vector store...")
        self.vector_store = FAISS.from_texts(chunks, self.embedding_model)
        print("Vector store created successfully.")
    
    def answer_question(self, question: str, k: int = 5) -> str:
        """Answer a question based on the content of the loaded PDF."""
        if not self.vector_store:
            return "Please load a PDF document first."
        
        # Retrieve relevant chunks
        print(f"Retrieving {k} most relevant chunks for question: {question}")
        docs = self.vector_store.similarity_search(question, k=k)
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # Generate prompt
        prompt = f"""
        You are a helpful assistant that accurately answers questions based on the provided context.
        If the answer cannot be found in the context, say "I don't have enough information to answer this question."
        Do not make up or infer information that is not explicitly stated in the context.
        
        Context:
        {context}
        
        Question: {question}
        
        Answer:
        """
        
        # Generate answer
        print("Generating answer...")
        response = self.llm.invoke(prompt)
        return response.content

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG system using Google Gemini")
    parser.add_argument("--api_key", type=str, help="Google Gemini API key")
    parser.add_argument("--pdf", type=str, help="Path to PDF file")
    
    args = parser.parse_args()
    
    if not args.api_key:
        api_key = input("Enter your Google Gemini API key: ")
    else:
        api_key = args.api_key
    
    rag = RAGSystem(api_key)
    
    if args.pdf:
        rag.process_pdf(args.pdf)
    
    # Interactive Q&A loop
    print("\nRAG System Ready! Enter 'quit' or 'exit' to end the session.")
    print("Enter 'load' followed by a PDF path to load a new document.")
    
    while True:
        user_input = input("\nQuestion: ")
        
        if user_input.lower() in ["quit", "exit"]:
            break
        
        if user_input.lower().startswith("load "):
            pdf_path = user_input[5:].strip()
            rag.process_pdf(pdf_path)
            continue
        
        if not rag.vector_store:
            print("Please load a PDF document first using 'load <pdf_path>'")
            continue
        
        answer = rag.answer_question(user_input)
        print(f"\nAnswer: {answer}")
