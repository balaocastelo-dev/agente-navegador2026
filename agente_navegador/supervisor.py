"""
Módulo supervisor — gerencia checkpoints humanos e confirmações de ações críticas.
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from agente_navegador.logger import get_logger, log_checkpoint

console = Console()
log = get_logger(__name__)


def human_checkpoint(message: str) -> bool:
    """
    Pausa a execução e aguarda confirmação humana.
    Retorna True se o usuário confirmar, False se cancelar.
    """
    log_checkpoint(message)

    console.print(
        Panel(
            f"[bold yellow]{message}[/bold yellow]\n\n"
            "[dim]Realize a ação manualmente no navegador e confirme para continuar.[/dim]",
            title="[bold red]⏸  AGUARDANDO SUPERVISOR HUMANO[/bold red]",
            border_style="yellow",
            expand=False,
        )
    )

    try:
        confirmed = Confirm.ask(
            "\n[bold]✔ Ação concluída? Continuar execução?[/bold]",
            default=True,
        )
    except (KeyboardInterrupt, EOFError):
        console.print("\n[bold red]Execução interrompida pelo usuário.[/bold red]")
        return False

    if confirmed:
        log.info("Checkpoint aprovado pelo operador humano.")
    else:
        log.warning("Checkpoint NEGADO pelo operador humano — execução pausada.")

    return confirmed


def confirm_critical_action(action_description: str) -> bool:
    """
    Pede confirmação explícita antes de uma ação crítica.
    Mesmo que o plano tenha passado pela validação de segurança,
    o supervisor pede confirmação em runtime.
    """
    console.print(
        Panel(
            f"[bold red]⚠  AÇÃO CRÍTICA DETECTADA:[/bold red]\n\n"
            f"[bold white]{action_description}[/bold white]\n\n"
            "[dim]Esta ação pode ter consequências irreversíveis.[/dim]\n"
            "[dim]Revise cuidadosamente antes de confirmar.[/dim]",
            title="[bold red]🔒 CONFIRMAÇÃO OBRIGATÓRIA[/bold red]",
            border_style="red",
            expand=False,
        )
    )

    try:
        confirmed = Confirm.ask(
            "[bold red]Confirma a execução desta ação crítica?[/bold red]",
            default=False,
        )
    except (KeyboardInterrupt, EOFError):
        console.print("\n[bold red]Execução interrompida pelo usuário.[/bold red]")
        return False

    if confirmed:
        log.warning(f"Ação crítica APROVADA pelo operador: {action_description}")
    else:
        log.info(f"Ação crítica REJEITADA pelo operador: {action_description}")

    return confirmed


def prompt_user(message: str, default: str = "") -> str:
    """
    Exibe um prompt para entrada do usuário.
    Usado quando o plano precisa de um valor fornecido pelo operador.
    """
    try:
        return Prompt.ask(f"[bold cyan]📝 {message}[/bold cyan]", default=default)
    except (KeyboardInterrupt, EOFError):
        return default
