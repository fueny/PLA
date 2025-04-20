import os
from pathlib import Path
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FakeEmbeddings
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import StateGraph, END, START
from typing import Dict, TypedDict, List, Any, Tuple, Union
import logging

# Import our configuration
from config import Config

# Import timer for runtime management
from timer import RuntimeTimer, timer_decorator, timed_section

# Configure logging
logger = logging.getLogger(__name__)

# Define state types for LangGraph
class GraphState(TypedDict):
    question: str
    context: List[str]
    answer: str
    documents: List[str]
    summary: Dict[str, Any]
    chinese_summary: Dict[str, Any]  # 添加中文总结字段

# Initialize embeddings and vector database
embeddings = FakeEmbeddings(size=1536)  # 使用 FakeEmbeddings 作为替代
vectordb = Chroma(persist_directory=str(Config.VECTORDB_DIR), embedding_function=embeddings)

# Create a retriever
retriever = vectordb.as_retriever(search_kwargs={"k": 5})

# Define LLM - use a fallback mechanism to try different models
def get_llm():
    """Initialize LLM based on configuration."""
    preferred_model = Config.get_preferred_model()

    if not preferred_model:
        raise ValueError("No valid API keys found. At least one API key is required to run this program.")

    provider = preferred_model["provider"]
    config = preferred_model["config"]

    logger.info(f"Using {provider} model: {config['name']}")

    try:
        if provider == "OpenAI":
            if config.get("api_base"):
                logger.info(f"Using custom API base: {config['api_base']}")
                return ChatOpenAI(
                    model_name=config["name"],
                    openai_api_key=config["api_key"],
                    openai_api_base=config["api_base"],
                    temperature=config["temperature"]
                )
            else:
                return ChatOpenAI(
                    model_name=config["name"],
                    openai_api_key=config["api_key"],
                    temperature=config["temperature"]
                )

        elif provider == "Grok":
            # For Grok, we use the OpenAI client with custom base URL
            return ChatOpenAI(
                model_name=config["name"],
                openai_api_key=config["api_key"],
                openai_api_base=config["api_base"],
                temperature=config["temperature"]
            )

        elif provider == "Anthropic":
            # Import here to avoid dependency issues if not used
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model_name=config["name"],
                anthropic_api_key=config["api_key"],
                temperature=config["temperature"]
            )

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    except Exception as e:
        logger.error(f"{provider} initialization failed: {e}")
        raise  # If initialization fails, directly raise the exception

# Get LLM
llm = get_llm()

# Define prompts
retrieval_prompt = PromptTemplate.from_template(
    """You are an AI assistant tasked with analyzing academic documents.

    Based on the following context, please answer the question thoroughly.

    Context: {context}

    Question: {question}

    Answer:"""
)

summary_prompt = PromptTemplate.from_template(
    """You are an AI assistant tasked with creating comprehensive summaries of academic documents.

    Based on the following information extracted from multiple documents, create a detailed summary that includes:
    1. Key points from each document
    2. Important concepts and ideas
    3. Connections and relationships between the documents
    4. Any significant findings or conclusions

    Information:
    {context}

    Please format your response as a well-structured markdown document with appropriate headings, subheadings, and bullet points.
    """
)

# Define Chinese summary prompt
chinese_summary_prompt = PromptTemplate.from_template(
    """You are an AI assistant tasked with creating comprehensive summaries of academic documents in Chinese.

    Based on the following information extracted from multiple documents, create a detailed summary in Chinese (Simplified Chinese) that includes:
    1. Key points from each document (每份文档的要点)
    2. Important concepts and ideas (重要概念和想法)
    3. Connections and relationships between the documents (文档之间的联系和关系)
    4. Any significant findings or conclusions (重要发现或结论)

    Information:
    {context}

    Please format your response as a well-structured markdown document with appropriate headings, subheadings, and bullet points in Chinese.
    """
)

# Define LangChain retrieval chain
def retrieval_chain(state):
    question = state["question"]
    docs = retriever.get_relevant_documents(question)
    state["context"] = [doc.page_content for doc in docs]
    state["documents"] = [doc.metadata.get("source", "unknown") for doc in docs]
    return state

# Define answer generation node
def generate_answer(state):
    context = "\n\n".join(state["context"])
    chain = retrieval_prompt | llm | StrOutputParser()
    state["answer"] = chain.invoke({"context": context, "question": state["question"]})
    return state

# Define summary generation node
def generate_summary(state):
    # Collect all answers and contexts
    all_content = state["context"] + [state["answer"]]
    full_context = "\n\n".join(all_content)

    # Generate summary
    chain = summary_prompt | llm | StrOutputParser()
    summary = chain.invoke({"context": full_context})

    # Store in state
    state["summary"] = {
        "content": summary,
        "sources": state["documents"],
        "question": state["question"]
    }
    return state

# Define Chinese summary generation node
def generate_chinese_summary(state):
    # Check if summary exists
    if "summary" not in state or not state["summary"]:
        logger.warning("No English summary found. Cannot generate Chinese summary.")
        return state

    # Use the English summary as context for the Chinese summary
    english_summary = state["summary"]["content"]

    # Generate Chinese summary
    logger.info("Generating Chinese summary...")
    chain = chinese_summary_prompt | llm | StrOutputParser()
    chinese_summary = chain.invoke({"context": english_summary})

    # Store in state
    state["chinese_summary"] = {
        "content": chinese_summary,
        "sources": state["documents"],
        "question": state["question"]
    }
    return state

# Define should end function
def should_end(state):
    return "chinese_summary" in state and state["chinese_summary"] is not None

# Build LangGraph
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("retrieval", retrieval_chain)
workflow.add_node("answer_generation", generate_answer)
workflow.add_node("summary_generation", generate_summary)
workflow.add_node("chinese_summary_generation", generate_chinese_summary)

# Add edges - including START edge
workflow.add_edge(START, "retrieval")
workflow.add_edge("retrieval", "answer_generation")
workflow.add_edge("answer_generation", "summary_generation")
workflow.add_edge("summary_generation", "chinese_summary_generation")
workflow.add_edge("chinese_summary_generation", END)

# Compile the graph
graph = workflow.compile()

@timer_decorator(task_name="Process Documents with LangGraph")
def process_documents() -> Tuple[Path, Path]:
    """Process documents and generate a summary."""
    # Ensure directories exist
    Config.ensure_directories_exist()

    # Define questions to analyze the documents
    questions = [
        "What are the key concepts in artificial intelligence?",
        "What are the fundamentals of quantum computing?",
        "What are the main points about climate change?",
        "What connections exist between these topics?",
        "What are the important ideas across all documents?"
    ]

    # Process each question
    results = []
    for i, question in enumerate(questions):
        logger.info(f"Processing question {i+1}/{len(questions)}: {question}")
        with timed_section(f"Question {i+1}: {question[:30]}..."):
            result = graph.invoke({"question": question})
            results.append(result)

    # Combine all summaries into a final summary
    with timed_section("Generate English Summary"):
        final_summary = """# Comprehensive Summary of Documents

## Overview
This document provides a comprehensive summary of the key points, important concepts, and connections between multiple documents on artificial intelligence, quantum computing, and climate change.

"""

        # Add individual summaries
        for i, result in enumerate(results):
            if "summary" in result and "content" in result["summary"]:
                final_summary += f"\n## Analysis {i+1}: {result['summary']['question']}\n\n"
                final_summary += result["summary"]["content"]
                final_summary += "\n\n"

        # Add sources section
        final_summary += "\n## Sources\n\n"
        all_sources = set()
        for result in results:
            if "summary" in result and "sources" in result["summary"]:
                all_sources.update(result["summary"]["sources"])

        for source in all_sources:
            final_summary += f"- {source}\n"

        # Write the final summary to a file
        summary_path = Config.OUTPUT_DIR / 'summary.md'
        with open(summary_path, "w") as f:
            f.write(final_summary)

        logger.info(f"Summary generated and saved to {summary_path}")

    # Generate Chinese summary
    logger.info("Generating comprehensive Chinese summary...")

    with timed_section("Generate Chinese Summary"):
        # Create Chinese summary template
        chinese_final_summary = """# 文档综合摘要

## 概述
本文档提供了关于人工智能、量子计算和气候变化的多份文档的要点、重要概念和联系的综合摘要。

"""

        # Add individual Chinese summaries
        for i, result in enumerate(results):
            if "chinese_summary" in result and "content" in result["chinese_summary"]:
                chinese_final_summary += f"\n## 分析 {i+1}: {result['chinese_summary']['question']}\n\n"
                chinese_final_summary += result["chinese_summary"]["content"]
                chinese_final_summary += "\n\n"

        # Add sources section
        chinese_final_summary += "\n## 来源\n\n"
        for source in all_sources:
            chinese_final_summary += f"- {source}\n"

        # Write the Chinese summary to a file
        chinese_summary_path = Config.OUTPUT_DIR / 'summary_chinese.md'
        with open(chinese_summary_path, "w") as f:
            f.write(chinese_final_summary)

        logger.info(f"Chinese summary generated and saved to {chinese_summary_path}")

    return summary_path, chinese_summary_path

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Print configuration
    Config.print_configuration()

    # Process documents
    process_documents()
