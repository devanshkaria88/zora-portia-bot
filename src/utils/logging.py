"""
Custom logging utilities for the Zora trading bot
"""
import logging
import sys
from datetime import datetime
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors and symbols to log messages"""
    
    # Format strings for different levels
    FORMATS = {
        logging.DEBUG: f"{Fore.CYAN}🔍 {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {Fore.CYAN}DEBUG:{Fore.RESET} {{message}}",
        logging.INFO: f"{Fore.GREEN}ℹ️  {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {Fore.GREEN}INFO:{Fore.RESET} {{message}}",
        logging.WARNING: f"{Fore.YELLOW}⚠️  {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {Fore.YELLOW}WARNING:{Fore.RESET} {{message}}",
        logging.ERROR: f"{Fore.RED}❌ {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {Fore.RED}ERROR:{Fore.RESET} {{message}}",
        logging.CRITICAL: f"{Fore.RED}{Style.BRIGHT}🚨 {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {Fore.RED}{Style.BRIGHT}CRITICAL:{Style.RESET_ALL} {{message}}",
    }
    
    # Special formats for certain message patterns
    SPECIAL_FORMATS = [
        # WebSocket messages
        (
            "WebSocket", 
            f"{Fore.MAGENTA}🔌 {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {Fore.MAGENTA}WEBSOCKET:{Fore.RESET} {{message}}"
        ),
        # Signal messages
        (
            "Signal", 
            f"{Fore.YELLOW}🔔 {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {Fore.YELLOW}SIGNAL:{Fore.RESET} {{message}}"
        ),
        # Buy signals - raw message with custom emoji
        (
            "BUY Signal", 
            f"🟢 {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {{message}}"
        ),
        # Sell signals - raw message with custom emoji
        (
            "SELL Signal", 
            f"🔴 {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {{message}}"
        ),
        # Hold signals - raw message with custom emoji
        (
            "HOLD Signal", 
            f"🟡 {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {{message}}"
        ),
        # Buy action - force green
        (
            "Would BUY", 
            f"{Fore.GREEN}💱 {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {Fore.GREEN}TRADE:{Fore.RESET} {Fore.GREEN}{{message}}{Style.RESET_ALL}"
        ),
        # Sell action - force red
        (
            "Would SELL", 
            f"{Fore.RED}💱 {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {Fore.RED}TRADE:{Fore.RESET} {Fore.RED}{{message}}{Style.RESET_ALL}"
        ),
        # New block messages
        (
            "New block", 
            f"{Fore.CYAN}⛓️  {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {Fore.CYAN}BLOCK:{Fore.RESET} {{message}}"
        ),
        # Trade messages
        (
            "Trade", 
            f"{Fore.GREEN}💱 {{asctime}} [{Fore.BLUE}{{name}}{Fore.RESET}] {Fore.GREEN}TRADE:{Fore.RESET} {{message}}"
        ),
    ]
    
    def format(self, record):
        # Get the base format for this log level
        log_format = self.FORMATS.get(record.levelno)
        
        # Check for special message patterns
        for pattern, special_format in self.SPECIAL_FORMATS:
            if pattern in record.getMessage():
                log_format = special_format
                break
        
        # Format the time more concisely
        record.asctime = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Set the actual format string
        formatter = logging.Formatter(log_format, style='{')
        return formatter.format(record)

class QuietTradesOnlyFilter(logging.Filter):
    """Filter that allows only trade-related log messages and critical errors"""
    
    def filter(self, record):
        """Return True if we want to keep this log record, False otherwise"""
        # Allow critical errors (but not WebSocket errors)
        if record.levelno >= logging.ERROR:
            # Skip WebSocket errors
            if "WebSocket:" in record.getMessage():
                return False
            return True
            
        # Allow portfolio display
        if "PORTFOLIO FOR" in record.getMessage():
            return True
            
        # Allow trading account status
        if "TRADING ACCOUNT STATUS" in record.getMessage():
            return True
            
        # Allow trade-related messages
        trade_keywords = [
            "TRADE:", "BOUGHT", "SOLD", "TRADE FAILED", "Portfolio value change:", "Initial Capital:"
        ]
        
        # Check if any trade keyword is in the message
        message = record.getMessage()
        
        # Always exclude WebSocket messages
        if "WebSocket:" in message:
            return False
            
        return any(keyword in message for keyword in trade_keywords)

class SignalsOnlyFilter(logging.Filter):
    """Filter that allows only signal-related log messages"""
    
    def filter(self, record):
        """Return True if we want to keep this log record, False otherwise"""
        # Only show high-level signal messaging
        signal_keywords = [
            "BUY Signal", "SELL Signal", "HOLD Signal", 
            "Would BUY", "Would SELL", "Signal: Processing"
        ]
        
        # Check if any signal keyword is in the message
        message = record.getMessage()
        
        # Skip detailed trade fetching logs
        if "Fetching recent transfers" in message or "Falling back to RPC" in message:
            return False
            
        return any(keyword in message for keyword in signal_keywords)

def setup_logging(log_file=None, console_level=logging.INFO, file_level=logging.DEBUG):
    """
    Set up logging with colored console output and optional file output
    
    Args:
        log_file: Optional path to log file
        console_level: Logging level for console output
        file_level: Logging level for file output
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all logs, filter at handler level
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(ColoredFormatter())
    root_logger.addHandler(console_handler)
    
    # File handler if requested
    if log_file:
        # File logs don't have colors, use a plain formatter
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(file_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger

def setup_signals_only_logging(log_file=None):
    """
    Set up logging that only shows signal-related messages
    
    Args:
        log_file: Optional path to log file
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter())
    
    # Add the signals-only filter
    console_handler.addFilter(SignalsOnlyFilter())
    
    root_logger.addHandler(console_handler)
    
    # File handler if requested
    if log_file:
        # File logs don't have colors, use a plain formatter
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(file_formatter)
        # No filter for file handler to maintain complete logs
        root_logger.addHandler(file_handler)
    
    return root_logger

def setup_quiet_trading_logging(log_file=None):
    """
    Set up logging that only shows trade-related messages and errors
    
    Args:
        log_file: Optional path to log file
    """
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter())
    
    # Add the trades-only filter
    console_handler.addFilter(QuietTradesOnlyFilter())
    
    root_logger.addHandler(console_handler)
    
    # File handler if requested - keeps all logs for debugging
    if log_file:
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        # No filter for file handler to maintain complete logs
        root_logger.addHandler(file_handler)
    
    return root_logger
