"""
Módulo de carregamento e validação de planos YAML.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml

from agente_navegador.logger import get_logger
from agente_navegador.models import Plan
from agente_navegador.safety import validate_plan_safety

log = get_logger(__name__)


def load_plan(path: str | Path) -> Plan:
    """
    Carrega e valida um plano YAML.

    Raises:
        FileNotFoundError: Se o arquivo não existir.
        ValueError: Se o plano for inválido.
    """
    plan_path = Path(path)
    if not plan_path.exists():
        raise FileNotFoundError(f"Arquivo de plano não encontrado: {plan_path}")

    log.info(f"Carregando plano: {plan_path.name}")

    with open(plan_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw:
        raise ValueError(f"Arquivo de plano vazio: {plan_path}")

    try:
        plan = Plan.model_validate(raw)
    except Exception as exc:
        raise ValueError(f"Plano inválido ({plan_path.name}): {exc}") from exc

    log.info(f"Plano '{plan.name}' carregado com {len(plan.steps)} passos.")
    return plan


def validate_plan(path: str | Path) -> tuple[bool, List[str]]:
    """
    Valida estrutura e segurança de um plano YAML.
    Retorna (válido: bool, erros: List[str]).
    """
    try:
        plan = load_plan(path)
    except (FileNotFoundError, ValueError) as e:
        return False, [str(e)]

    safety_errors = validate_plan_safety(plan.steps)
    if safety_errors:
        return False, safety_errors

    return True, []


def list_plans(plans_dir: Optional[str | Path] = None) -> List[Path]:
    """Lista todos os planos YAML disponíveis no diretório de planos."""
    from agente_navegador.config import config

    directory = Path(plans_dir) if plans_dir else config.plans_dir
    if not directory.exists():
        return []
    return sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))
