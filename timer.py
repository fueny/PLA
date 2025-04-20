#!/usr/bin/env python3
"""
Runtime Timer Module for PDF Processing System

This module provides a structured way to track and manage execution time
during the PDF processing workflow. It updates every 15 seconds and can
be easily integrated into different parts of the application.

The module is designed to be modular and can be easily removed if not needed.

Usage:
    from timer import RuntimeTimer, timer_decorator

    # As a context manager
    with RuntimeTimer("Processing documents"):
        # Your code here
        process_documents()

    # As a decorator
    @timer_decorator
    def my_function():
        # Your code here
        pass

    # As a standalone timer
    timer = RuntimeTimer("Long-running task")
    timer.start()
    # Your code here
    timer.stop()
"""

import time
import threading
import logging
import functools
from typing import Optional, Callable, Any
from contextlib import contextmanager

# Configure logging
logger = logging.getLogger(__name__)

class RuntimeTimer:
    """
    A timer class to track execution time with periodic updates.
    
    This class can be used as a context manager, standalone timer,
    or through the timer_decorator function.
    """
    
    def __init__(self, task_name: str, update_interval: int = 15):
        """
        Initialize the timer.
        
        Args:
            task_name: Name of the task being timed
            update_interval: Interval in seconds for progress updates (default: 15)
        """
        self.task_name = task_name
        self.update_interval = update_interval
        self.start_time = 0.0
        self.end_time = 0.0
        self.is_running = False
        self.timer_thread = None
        self.total_time = 0.0
    
    def start(self) -> None:
        """Start the timer and begin periodic updates."""
        if self.is_running:
            logger.warning(f"Timer for '{self.task_name}' is already running.")
            return
        
        self.start_time = time.time()
        self.is_running = True
        logger.info(f"Started timer for '{self.task_name}'")
        
        # Start a thread for periodic updates
        self.timer_thread = threading.Thread(
            target=self._update_progress,
            daemon=True
        )
        self.timer_thread.start()
    
    def stop(self) -> float:
        """
        Stop the timer and return the elapsed time.
        
        Returns:
            float: Total elapsed time in seconds
        """
        if not self.is_running:
            logger.warning(f"Timer for '{self.task_name}' is not running.")
            return self.total_time
        
        self.end_time = time.time()
        self.is_running = False
        self.total_time = self.end_time - self.start_time
        
        # Wait for the timer thread to finish if it's still running
        if self.timer_thread and self.timer_thread.is_alive():
            self.timer_thread.join(timeout=1.0)
        
        logger.info(f"Completed '{self.task_name}' in {self.total_time:.2f} seconds")
        return self.total_time
    
    def _update_progress(self) -> None:
        """Periodically log the elapsed time while the timer is running."""
        while self.is_running:
            time.sleep(self.update_interval)
            if self.is_running:  # Check again after sleep
                elapsed = time.time() - self.start_time
                logger.info(f"'{self.task_name}' running for {elapsed:.2f} seconds...")
    
    def __enter__(self) -> 'RuntimeTimer':
        """Context manager entry point."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit point."""
        self.stop()
        if exc_type:
            logger.error(f"An error occurred during '{self.task_name}': {exc_val}")


def timer_decorator(func: Optional[Callable] = None, task_name: Optional[str] = None) -> Callable:
    """
    Decorator to time the execution of a function.
    
    Args:
        func: The function to be timed
        task_name: Optional custom name for the task (defaults to function name)
    
    Returns:
        Callable: Decorated function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal task_name
            if task_name is None:
                task_name = f.__name__
            
            with RuntimeTimer(task_name):
                return f(*args, **kwargs)
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func)


# Singleton timer for global use
_global_timer: Optional[RuntimeTimer] = None

def start_global_timer(task_name: str) -> None:
    """
    Start a global timer that can be accessed from anywhere.
    
    Args:
        task_name: Name of the task being timed
    """
    global _global_timer
    if _global_timer is not None and _global_timer.is_running:
        logger.warning("A global timer is already running. Stopping it first.")
        _global_timer.stop()
    
    _global_timer = RuntimeTimer(task_name)
    _global_timer.start()

def stop_global_timer() -> float:
    """
    Stop the global timer and return the elapsed time.
    
    Returns:
        float: Total elapsed time in seconds
    """
    global _global_timer
    if _global_timer is None or not _global_timer.is_running:
        logger.warning("No global timer is running.")
        return 0.0
    
    return _global_timer.stop()

@contextmanager
def timed_section(section_name: str) -> None:
    """
    Context manager for timing a section of code.
    
    Args:
        section_name: Name of the code section being timed
    """
    timer = RuntimeTimer(section_name)
    timer.start()
    try:
        yield
    finally:
        timer.stop()
