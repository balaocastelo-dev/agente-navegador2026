"""
Módulo de logging estruturado com Rich.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# Tema Rich personalizado (vermelho/branco/preto — identidade Balão)
_THEME = Theme(
    {
        "info": "bold white",
        "warning": "bold yellow",
        "error": "bold red",
        "critical": "bold white on red",
        "success": "bold green",
        "checkpoint": "bold magenta",
        "agent": "bold cyan",
    }
)

console = Console(theme=_THEME)


def get_logger(name: str = "agente_navegador") -> logging.Logger:
    """
    Retorna um logger configurado com Rich (console) e FileHandler (arquivo).
    """
    from agente_navegador.config import config  # import tardio p/ evitar circular

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # já configurado

    logger.setLevel(logging.DEBUG)

    # --- Handler Console (Rich) ---
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
    )
    rich_handler.setLevel(logging.INFO)
    logger.addHandler(rich_handler)

    # --- Handler Arquivo ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = config.log_dir / f"agente_{timestamp}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def log_checkpoint(message: str) -> None:
    """Exibe um checkpoint humano de forma destacada."""
    console.rule("[checkpoint]🔵 CHECKPOINT HUMANO[/checkpoint]")
    console.print(f"[checkpoint]{message}[/checkpoint]")
    console.rule()


def log_blocked(action: str, reason: str) -> None:
    """Exibe uma ação bloqueada de forma destacada."""
    console.rule("[error]🚫 AÇÃO BLOQUEADA[/error]")
    console.print(f"[error]Ação:[/error] {action}")
    console.print(f"[error]Motivo:[/error] {reason}")
    console.rule()


def log_success(message: str) -> None:
    console.print(f"[success]✅ {message}[/success]")


def log_agent(message: str) -> None:
    console.print(f"[agent]🤖 {message}[/agent]")
