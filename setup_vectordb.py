import os
from pathlib import Path
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import MarkdownTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FakeEmbeddings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Define paths
markdown_dir = Path('./output/markdown')
db_dir = Path('./output/vectordb')

# Ensure vector database directory exists
os.makedirs(db_dir, exist_ok=True)

# Get all markdown files
markdown_files = list(markdown_dir.glob('*.md'))
print(f"Found {len(markdown_files)} markdown files to process")

# Initialize document list
documents = []

# Load and process each markdown file
for md_file in markdown_files:
    print(f"Processing {md_file.name}...")

    # Load the markdown file
    loader = TextLoader(md_file)
    docs = loader.load()

    # Add metadata to identify source file
    for doc in docs:
        doc.metadata['source'] = md_file.name

    # Add to documents list
    documents.extend(docs)

# Split documents into chunks
text_splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=200)
splits = text_splitter.split_documents(documents)

print(f"Split documents into {len(splits)} chunks")

# Initialize embeddings - using FakeEmbeddings as a lightweight alternative
embeddings = FakeEmbeddings(size=1536)

# Create and persist the vector database
vectordb = Chroma.from_documents(
    documents=splits,
    embedding=embeddings,
    persist_directory=str(db_dir)
)

# Persist the database
vectordb.persist()

print(f"Vector database created and persisted at {db_dir}")
