# This file is part of the MCP-Server project for logging and console management.
# Author: shiboli
# date: 2025-06-11
# Version: 0.1.0

import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import track as rich_track
from rich.theme import Theme

# Define a custom logging level for success messages
SUCCESS_LEVEL_NUM = 25

try:
    logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")
except AttributeError:
    pass  # Level already exists

def success_log(self, message, *args, **kwargs):
    if self.isEnabledFor(SUCCESS_LEVEL_NUM):
        self._log(SUCCESS_LEVEL_NUM, message, args, **kwargs)

# Register the custom success method to the logging.Logger class
if not hasattr(logging.Logger, 'success'):
    setattr(logging.Logger, 'success', success_log)

class ConsoleManager:
    """
    A singleton class that manages the console output for the MCP-Server.
    It uses Rich for beautiful logging and console output.
    """
    def __init__(self):
        # Initialize the console with a custom theme
        custom_theme = Theme({
            "logging.level.success": "bold green"
        })
        self._console = Console(theme=custom_theme)
        self._logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        # Get the logger instance for our specific project
        logger = logging.getLogger("MCP-Server")
        if logger.hasHandlers():
            # If logger is already configured, don't add handlers again
            return logger
        
        logger.setLevel(logging.INFO)
        handler = RichHandler(
            console=self._console,
            rich_tracebacks=True,
            tracebacks_show_locals=False, # Set to True for more detailed tracebacks
            keywords=["INFO", "SUCCESS", "WARNING", "ERROR", "DEBUG", "CRITICAL"],
            show_path=False
        )
        handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="[%X]"))
        logger.addHandler(handler)
        return logger

    # Define logging methods
    def info(self, message: str):
        self._logger.info(message)

    def success(self, message: str):
        # The custom level name is already "SUCCESS", no need to add a prefix
        self._logger.success(message)

    def warning(self, message: str):
        self._logger.warning(message)

    def error(self, message: str):
        self._logger.error(message)
        
    def exception(self, message: str):
        # The 'exc_info=True' is what makes .exception() special
        self._logger.exception(message)

    # Define higher-level console methods
    def rule(self, title: str, style: str = "cyan"):
        self._console.rule(f"[bold {style}]{title}[/bold {style}]", style=style)

    def display_data_as_table(self, data: dict, title:str):
        table = Table(show_header=True, header_style="bold magenta", box=None, show_edge=False)
        table.add_column("Parameter", style="cyan", no_wrap=True, width=20)
        table.add_column("Value", style="white")

        for key, value in data.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    table.add_row(f"  • {key}.{sub_key}", str(sub_value))
            elif isinstance(value, list):
                table.add_row(key, ", ".join(map(str, value or [])))
            else:
                table.add_row(key, str(value))
        
        panel = Panel(table, title=f"[bold green]✓ {title}[/bold green]", border_style="green")
        self._console.print(panel)

    def display_error_panel(self, title: str, error_message: str):
        panel = Panel(error_message, title=f"[bold red]{title}[/bold red]", border_style="red")
        self._console.print(panel)

    def track(self, *args, **kwargs):
        return rich_track(*args, **kwargs)

# Create a singleton instance for global use
console = ConsoleManager()


# Test block
if __name__ == "__main__":
    console.rule("ConsoleManager Test Suite")
    console.info("This is an info message.")
    console.success("This is a success message.")
    console.warning("This is a warning message.")
    console.error("This is an error message.")
    try:
        1 / 0
    except ZeroDivisionError:
        console.exception("This is an exception message with traceback.")