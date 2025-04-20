#!/usr/bin/env python3
"""
PDF Processing System - Main Script

This script orchestrates the entire PDF processing workflow:
1. Convert PDFs to markdown
2. Setup vector database from markdown files
3. Process documents and generate summaries

Usage:
    python3 main.py --all                # Run all steps
    python3 main.py --convert            # Only convert PDFs to markdown
    python3 main.py --setup-db           # Only setup vector database
    python3 main.py --process            # Only process documents
    python3 main.py --config             # Display configuration information
"""

import sys
import os
import argparse
import logging

# Import our configuration
from config import Config

# Import timer for runtime management
from timer import RuntimeTimer, timer_decorator, timed_section

# Ensure logs directory exists
os.makedirs(Config.LOGS_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Configure file handler for error logs only
file_handler = logging.FileHandler(Config.LOGS_DIR / 'error.log')
file_handler.setLevel(logging.ERROR)  # Only log errors to file
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Configure console logging separately (for info level)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Get the root logger and add file handler
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)

# Configure module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.handlers = []  # Remove default handlers
logger.addHandler(console_handler)  # Add console handler

def setup_directories():
    """Create necessary directories if they don't exist."""
    # Use the Config class to ensure all directories exist
    Config.ensure_directories_exist()
    logger.info("All required directories have been created.")

def check_pdf_files():
    """Check if there are PDF files in the input directory."""
    pdf_files = list(Config.INPUT_DIR.glob('*.pdf'))
    if not pdf_files:
        logger.error("No PDF files found in the input directory. Please add PDF files to the input directory.")
        print("\nNo PDF files found in the input directory.")
        print(f"Please add PDF files to: {Config.INPUT_DIR}")
        print("Then run the program again.\n")
        return False
    logger.info(f"Found {len(pdf_files)} PDF files in the input directory.")
    return True

@timer_decorator(task_name="Convert PDFs to Markdown")
def convert_pdfs_to_markdown():
    """Convert PDF files to markdown format."""
    logger.info("Converting PDFs to markdown...")
    try:
        import convert_pdfs
        logger.info("PDFs converted to markdown successfully.")
    except Exception as e:
        logger.error(f"Error converting PDFs: {e}")
        raise

@timer_decorator(task_name="Setup Vector Database")
def setup_vector_database():
    """Setup vector database from markdown files."""
    logger.info("Setting up vector database...")
    try:
        import setup_vectordb
        logger.info("Vector database setup successfully.")
    except Exception as e:
        logger.error(f"Error setting up vector database: {e}")
        raise

@timer_decorator(task_name="Process Documents")
def process_documents():
    """Process documents and generate summaries using LangGraph."""
    logger.info("Processing documents...")
    try:
        import process_documents
        with timed_section("Generate Summaries"):
            summary_paths = process_documents.process_documents()

        # Handle both single path and tuple of paths
        if isinstance(summary_paths, tuple):
            english_path, chinese_path = summary_paths
            logger.info(f"Documents processed successfully.")
            logger.info(f"English summary saved to {english_path}")
            logger.info(f"Chinese summary saved to {chinese_path}")
        else:
            logger.info(f"Documents processed successfully. Summary saved to {summary_paths}")
    except Exception as e:
        logger.error(f"Error processing documents: {e}")
        raise

def check_api_keys():
    """Check if any API keys are configured."""
    # Use the Config class to validate configuration
    if not Config.validate_configuration():
        logger.error("No valid API keys found. At least one API key is required to run this program.")
        sys.exit(1)  # 如果没有有效的API密钥，直接退出程序

    # Print configuration information
    Config.print_configuration()

    return True

def select_model_provider():
    """Interactive prompt for selecting the model provider."""
    # Get available models
    available_models = Config.get_configured_models()

    if not available_models:
        logger.error("No models are configured. Please check your API keys.")
        sys.exit(1)

    # Print available options
    print("\n" + "=" * 50)
    print("Please select a model provider:")
    print("=" * 50)

    options = []
    if "OpenAI" in available_models:
        options.append(("A", "OpenAI", available_models["OpenAI"]["name"]))
    if "Grok" in available_models:
        options.append(("B", "Grok", available_models["Grok"]["name"]))
    if "Anthropic" in available_models:
        options.append(("C", "Anthropic", available_models["Anthropic"]["name"]))

    # Display options
    for key, provider, model in options:
        print(f"{key}) {provider} ({model})")

    # Get user selection
    while True:
        choice = input("\nEnter your choice (A/B/C): ").strip().upper()

        for key, provider, _ in options:
            if choice == key:
                if Config.set_model_provider(provider):
                    return

        print(f"Invalid choice. Please select one of: {', '.join([key for key, _, _ in options])}")

def main():
    """Main function to orchestrate the workflow."""
    parser = argparse.ArgumentParser(description="PDF Processing System")
    parser.add_argument("--all", action="store_true", help="Run all steps")
    parser.add_argument("--convert", action="store_true", help="Convert PDFs to markdown")
    parser.add_argument("--setup-db", action="store_true", help="Setup vector database")
    parser.add_argument("--process", action="store_true", help="Process documents")
    parser.add_argument("--config", action="store_true", help="Display configuration information")
    parser.add_argument("--no-timer", action="store_true", help="Disable runtime timer")

    args = parser.parse_args()

    # If only config flag is provided, just show configuration
    if args.config and not any(v for k, v in vars(args).items() if k != 'config' and v):
        Config.print_configuration()
        return

    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return

    # Start global timer if not disabled
    use_timer = not args.no_timer
    if use_timer:
        with RuntimeTimer("Total Execution"):
            _run_workflow(args)
    else:
        _run_workflow(args)

    logger.info("PDF Processing System completed successfully.")

def _run_workflow(args):
    """Execute the workflow based on provided arguments."""
    # Setup directories
    setup_directories()

    # Check if there are PDF files in the input directory
    if not check_pdf_files():
        return

    # Execute requested steps
    if args.convert or args.all:
        convert_pdfs_to_markdown()

    if args.setup_db or args.all:
        setup_vector_database()

    if args.process or args.all:
        # 检查 API 密钥并处理文档
        check_api_keys()  # 如果没有有效的 API 密钥，这个函数会直接退出程序

        # Interactive model selection
        select_model_provider()

        process_documents()

if __name__ == "__main__":
    main()
