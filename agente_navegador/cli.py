"""
CLI do Agente Navegador -- interface de linha de comando.

Uso:
    python -m agente_navegador.cli run plans/meta_whatsapp_setup.yaml --headed
    python -m agente_navegador.cli validate plans/meta_whatsapp_setup.yaml
    python -m agente_navegador.cli list-plans
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(
    name="agente-navegador",
    help="Agente Navegador Supervisionado -- Balao da Informatica Castelo",
    add_completion=False,
)
console = Console()

BANNER = """
[bold red]  Agente Navegador Supervisionado[/bold red]
[dim]  Balao da Informatica Castelo -- Av. Anchieta, 789 - Campinas/SP[/dim]
[dim]  v0.1.0[/dim]
"""


def show_banner() -> None:
    console.print(BANNER)


@app.command("run")
def run_plan(
    plan_path: Path = typer.Argument(..., help="Caminho para o arquivo de plano YAML"),
    headed: bool = typer.Option(True, "--headed/--headless", help="Abrir navegador visível"),
    skip_safety_check: bool = typer.Option(
        False, "--skip-safety-check", help="[PERIGOSO] Pular validação de segurança prévia"
    ),
) -> None:
    """Executa um plano YAML com o agente navegador supervisionado."""
    show_banner()

    from agente_navegador.collectors import load_plan, validate_plan
    from agente_navegador.logger import get_logger
    from agente_navegador.runner import PlanRunner

    log = get_logger()

    if not plan_path.exists():
        console.print(f"[bold red]ERRO: Arquivo nao encontrado: {plan_path}[/bold red]")
        raise typer.Exit(1)

    # Validação de segurança prévia
    if not skip_safety_check:
        console.print("[dim]Validando seguranca do plano...[/dim]")
        valid, errors = validate_plan(plan_path)
        if not valid:
            console.print("[bold red]ERRO: Plano com problemas de seguranca:[/bold red]")
            for err in errors:
                console.print(f"  [red]- {err}[/red]")
            console.print(
                "\n[dim]Use --skip-safety-check para ignorar (nao recomendado).[/dim]"
            )
            raise typer.Exit(1)
        console.print("[green]OK: Validacao de seguranca aprovada[/green]")

    try:
        plan = load_plan(plan_path)
    except Exception as exc:
        console.print(f"[bold red]ERRO ao carregar plano: {exc}[/bold red]")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold]Plano:[/bold] {plan.name}\n"
            f"[bold]Descricao:[/bold] {plan.description}\n"
            f"[bold]Passos:[/bold] {len(plan.steps)}\n"
            f"[bold]Modo:[/bold] {'headed (visivel)' if headed else 'headless'}",
            title="[bold red]>> Iniciando Execucao[/bold red]",
            border_style="red",
        )
    )

    runner = PlanRunner(plan=plan, headless=not headed)
    result = asyncio.run(runner.run())

    # Exibe resultado
    table = Table(title="Resultado da Execucao", border_style="dim")
    table.add_column("Campo", style="bold")
    table.add_column("Valor")
    table.add_row("Status", str(result.status.value))
    table.add_row("Passos concluidos", f"{result.steps_completed}/{result.steps_total}")
    table.add_row("Dados coletados", str(len(result.collected_data)))
    table.add_row("Screenshots", str(len(result.screenshots)))
    table.add_row("Erros", str(len(result.errors)))
    table.add_row("Acoes bloqueadas", str(len(result.blocked_actions)))
    console.print(table)

    if result.collected_data:
        console.print("\n[bold]Dados coletados:[/bold]")
        for item in result.collected_data:
            console.print(f"  [cyan]{item.key}[/cyan]: {item.value}")

    if result.errors:
        console.print("\n[bold red]Erros:[/bold red]")
        for err in result.errors:
            console.print(f"  [red]- {err}[/red]")

    exit_code = 0 if result.status.value in ("finished",) else 1
    raise typer.Exit(exit_code)


@app.command("validate")
def validate_plan_cmd(
    plan_path: Path = typer.Argument(..., help="Caminho para o arquivo de plano YAML"),
) -> None:
    """Valida a estrutura e segurança de um plano YAML sem executá-lo."""
    show_banner()
    from agente_navegador.collectors import validate_plan

    console.print(f"[dim]Validando: {plan_path}[/dim]")
    valid, errors = validate_plan(plan_path)

    if valid:
        console.print(
            Panel(
                "[bold green]OK: Plano valido! Nenhum problema encontrado.[/bold green]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                "\n".join(f"[red]- {e}[/red]" for e in errors),
                title="[bold red]ERRO: Problemas encontrados[/bold red]",
                border_style="red",
            )
        )
        raise typer.Exit(1)


@app.command("list-plans")
def list_plans_cmd() -> None:
    """Lista todos os planos YAML disponíveis."""
    show_banner()
    from agente_navegador.collectors import list_plans

    plans = list_plans()
    if not plans:
        console.print("[yellow]Nenhum plano encontrado no diretorio plans/[/yellow]")
        return

    table = Table(title="Planos Disponiveis", border_style="dim")
    table.add_column("Arquivo", style="bold cyan")
    table.add_column("Tamanho")

    for p in plans:
        size = f"{p.stat().st_size} bytes"
        table.add_row(p.name, size)

    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
