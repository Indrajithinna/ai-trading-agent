"""
Centralized Logging System
===========================
Provides structured logging for all agents and modules with file rotation.
"""

import os
import sys
import io
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime


class SafeStreamHandler(logging.StreamHandler):
    """Stream handler that safely handles Unicode on Windows."""
    
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            try:
                stream.write(msg + self.terminator)
            except UnicodeEncodeError:
                # Replace characters that can't be encoded
                safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
                stream.write(safe_msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


class TradingLogger:
    """Centralized logger with rotating file handler and colored console output."""
    
    _loggers: dict = {}
    
    @classmethod
    def get_logger(cls, name: str, log_level: str = "INFO") -> logging.Logger:
        """Get or create a logger instance."""
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        # Avoid duplicate handlers
        if not logger.handlers:
            # Console handler with safe Unicode handling
            try:
                # Try to set up UTF-8 stdout
                utf8_stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
                console_handler = SafeStreamHandler(utf8_stream)
            except (AttributeError, ValueError):
                console_handler = SafeStreamHandler()
            
            console_handler.setLevel(logging.INFO)
            console_fmt = logging.Formatter(
                "%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
                datefmt="%H:%M:%S"
            )
            console_handler.setFormatter(console_fmt)
            logger.addHandler(console_handler)
            
            # File handler with rotation
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, f"trading_{datetime.now().strftime('%Y%m%d')}.log")
            file_handler = RotatingFileHandler(
                log_file, maxBytes=10_000_000, backupCount=5, encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_fmt = logging.Formatter(
                "%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s"
            )
            file_handler.setFormatter(file_fmt)
            logger.addHandler(file_handler)
        
        cls._loggers[name] = logger
        return logger


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a logger."""
    return TradingLogger.get_logger(name)
