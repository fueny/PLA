#!/usr/bin/env python3
"""
Configuration management for PDF Processing System.

This module loads environment variables from .env file and provides
configuration settings for the application. It centralizes all configuration
management and ensures sensitive information is not hardcoded.

Usage:
    from config import Config

    # Access OpenAI configuration
    openai_api_key = Config.OPENAI_API_KEY
    openai_model = Config.OPENAI_MODEL

    # Check if a specific API is configured
    if Config.is_openai_configured():
        # Use OpenAI API
        ...
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration settings for the application."""

    # Base paths
    BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
    INPUT_DIR = BASE_DIR / 'input'
    OUTPUT_DIR = BASE_DIR / 'output'
    MARKDOWN_DIR = OUTPUT_DIR / 'markdown'
    IMAGES_DIR = MARKDOWN_DIR / 'images'
    VECTORDB_DIR = OUTPUT_DIR / 'vectordb'
    LOGS_DIR = BASE_DIR / 'logs'

    # API Keys (loaded from environment variables)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    GROK_API_KEY = os.getenv("GROK_API_KEY", "")

    # Model names - hardcoded with latest versions
    OPENAI_MODEL = "o3-mini"  # OpenAI's latest smaller reasoning model
    ANTHROPIC_MODEL = "claude-3-opus-20240229"  # Anthropic's most capable model
    GROK_MODEL = "grok-3-latest"  # xAI's latest model

    # API endpoints
    GROK_API_BASE = "https://api.xai.com/v1"

    # Vector database settings
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200

    # LLM generation settings
    # Temperature controls randomness: 0.0 = deterministic, 1.0 = creative
    # Lower values (0.0-0.3) are better for factual/analytical tasks
    # Higher values (0.7-1.0) are better for creative tasks
    TEMPERATURE = 0.2  # Default to low temperature for analytical summaries

    # Selected model provider (can be changed at runtime)
    SELECTED_PROVIDER = None

    @classmethod
    def is_openai_configured(cls) -> bool:
        """Check if OpenAI API is configured."""
        return bool(cls.OPENAI_API_KEY and cls.OPENAI_API_KEY != "your_openai_api_key")

    @classmethod
    def is_anthropic_configured(cls) -> bool:
        """Check if Anthropic API is configured."""
        return bool(cls.ANTHROPIC_API_KEY and cls.ANTHROPIC_API_KEY != "your_anthropic_api_key")

    @classmethod
    def is_grok_configured(cls) -> bool:
        """Check if Grok API is configured."""
        return bool(cls.GROK_API_KEY and cls.GROK_API_KEY != "your_grok_api_key")

    @classmethod
    def get_configured_models(cls) -> Dict[str, Dict[str, Any]]:
        """Get a dictionary of configured models with their settings."""
        models = {}

        if cls.is_openai_configured():
            models["OpenAI"] = {
                "name": cls.OPENAI_MODEL,
                "api_key": cls.OPENAI_API_KEY,
                "api_base": cls.OPENAI_API_BASE or None,
                "temperature": cls.TEMPERATURE
            }

        if cls.is_anthropic_configured():
            models["Anthropic"] = {
                "name": cls.ANTHROPIC_MODEL,
                "api_key": cls.ANTHROPIC_API_KEY,
                "temperature": cls.TEMPERATURE
            }

        if cls.is_grok_configured():
            models["Grok"] = {
                "name": cls.GROK_MODEL,
                "api_key": f"xai-{cls.GROK_API_KEY}",
                "api_base": cls.GROK_API_BASE,
                "temperature": cls.TEMPERATURE
            }

        return models

    @classmethod
    def set_model_provider(cls, provider: str) -> bool:
        """
        Set the selected model provider.

        Args:
            provider: The provider to use ("OpenAI", "Grok", or "Anthropic")

        Returns:
            bool: True if the provider was set successfully, False otherwise.
        """
        models = cls.get_configured_models()

        if provider in models:
            cls.SELECTED_PROVIDER = provider
            logger.info(f"Selected model provider: {provider}")
            return True
        else:
            logger.error(f"Provider {provider} is not configured or not available.")
            return False

    @classmethod
    def get_preferred_model(cls) -> Optional[Dict[str, Any]]:
        """
        Get the preferred model configuration based on availability or user selection.

        Returns:
            Dict containing model configuration or None if no models are configured.
        """
        models = cls.get_configured_models()

        # If a provider has been explicitly selected, use it
        if cls.SELECTED_PROVIDER and cls.SELECTED_PROVIDER in models:
            return {
                "provider": cls.SELECTED_PROVIDER,
                "config": models[cls.SELECTED_PROVIDER]
            }

        # Otherwise, use the default order of preference
        preference_order = ["OpenAI", "Grok", "Anthropic"]

        for provider in preference_order:
            if provider in models:
                return {
                    "provider": provider,
                    "config": models[provider]
                }

        return None

    @classmethod
    def ensure_directories_exist(cls) -> None:
        """Ensure all required directories exist."""
        os.makedirs(cls.INPUT_DIR, exist_ok=True)
        os.makedirs(cls.OUTPUT_DIR, exist_ok=True)
        os.makedirs(cls.MARKDOWN_DIR, exist_ok=True)
        os.makedirs(cls.IMAGES_DIR, exist_ok=True)
        os.makedirs(cls.VECTORDB_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)

        logger.info("All required directories have been created.")

    @classmethod
    def validate_configuration(cls) -> bool:
        """
        Validate the configuration and ensure at least one model is configured.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        if not any([cls.is_openai_configured(), cls.is_anthropic_configured(), cls.is_grok_configured()]):
            logger.error("No valid API keys found. At least one API key is required to run this program.")
            return False

        return True

    @classmethod
    def print_configuration(cls) -> None:
        """Print the current configuration (excluding sensitive information)."""
        logger.info("Current configuration:")

        # Print model availability
        if cls.is_openai_configured():
            logger.info(f"OpenAI API is configured with model: {cls.OPENAI_MODEL}")
            if cls.OPENAI_API_BASE:
                logger.info(f"Using custom API base: {cls.OPENAI_API_BASE}")
        else:
            logger.warning("OpenAI API is not configured")

        if cls.is_anthropic_configured():
            logger.info(f"Anthropic API is configured with model: {cls.ANTHROPIC_MODEL}")
        else:
            logger.warning("Anthropic API is not configured")

        if cls.is_grok_configured():
            logger.info(f"Grok API is configured with model: {cls.GROK_MODEL}")
        else:
            logger.warning("Grok API is not configured")

        # Print preferred model
        preferred = cls.get_preferred_model()
        if preferred:
            logger.info(f"Preferred model: {preferred['provider']} ({preferred['config']['name']})")
        else:
            logger.warning("No models are configured")

        # Print generation settings
        logger.info(f"Temperature: {cls.TEMPERATURE} ({'deterministic' if cls.TEMPERATURE < 0.3 else 'balanced' if cls.TEMPERATURE < 0.7 else 'creative'})")


# Validate configuration on import
if not Config.validate_configuration():
    logger.error("Invalid configuration. Please check your .env file.")
    sys.exit(1)
