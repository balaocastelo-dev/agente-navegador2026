"""
Módulo de segurança — define ações críticas e regras de bloqueio.

REGRA PRINCIPAL:
Qualquer ação crítica DEVE ser precedida por um human_checkpoint no plano YAML.
Caso contrário, o agente bloqueia a execução e registra o bloqueio.
"""
from __future__ import annotations

from typing import List, Set

from agente_navegador.logger import get_logger, log_blocked
from agente_navegador.models import ActionType, PlanStep

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Lista de ações críticas — palavras-chave que identificam sensibilidade
# ---------------------------------------------------------------------------
CRITICAL_KEYWORDS: Set[str] = {
    # Publicação / envio
    "publicar",
    "publish",
    "enviar",
    "send",
    "disparar",
    "blast",
    # WhatsApp oficial
    "conectar número",
    "connect number",
    "phone number",
    "register phone",
    # Pagamento
    "pagamento",
    "payment",
    "cobrança",
    "billing",
    "cartão",
    "credit card",
    # Remoção / exclusão
    "remover usuário",
    "remove user",
    "excluir app",
    "delete app",
    "excluir página",
    "delete page",
    "excluir conta",
    "delete account",
    # Termos / revisão
    "aceitar termos",
    "accept terms",
    "enviar para revisão",
    "submit for review",
    # Campanhas
    "ativar campanha",
    "activate campaign",
    "launch campaign",
    # Credenciais
    "alterar senha",
    "change password",
    "reset password",
    "gerar token",
    "generate token",
    "token permanente",
    "permanent token",
    "código 2fa",
    "2fa code",
    "two-factor",
    # Dados privados
    "baixar dados",
    "download data",
    "export data",
    "dados privados",
    # Spam
    "disparo em massa",
    "mass message",
    "bulk message",
    "spam",
}

# ---------------------------------------------------------------------------
# Ações que NUNCA podem ser automatizadas (bloqueio incondicional)
# ---------------------------------------------------------------------------
ABSOLUTELY_FORBIDDEN: Set[str] = {
    "salvar senha",
    "save password",
    "pedir código 2fa",
    "store cookies",
    "armazenar cookies",
    "burlar autenticação",
    "bypass authentication",
    "spam",
    "disparo em massa",
    "mass message",
    "bulk message",
}


def is_critical_action(step: PlanStep) -> bool:
    """
    Retorna True se o passo contém palavras-chave críticas nos campos
    url, value, message ou selector.
    """
    fields_to_check: List[str] = [
        step.url or "",
        step.value or "",
        step.message or "",
        step.selector or "",
        step.name or "",
    ]
    combined = " ".join(fields_to_check).lower()
    return any(keyword in combined for keyword in CRITICAL_KEYWORDS)


def is_absolutely_forbidden(step: PlanStep) -> bool:
    """
    Retorna True se o passo tenta algo absolutamente proibido.
    """
    fields_to_check: List[str] = [
        step.url or "",
        step.value or "",
        step.message or "",
        step.selector or "",
    ]
    combined = " ".join(fields_to_check).lower()
    return any(keyword in combined for keyword in ABSOLUTELY_FORBIDDEN)


def validate_plan_safety(steps: list) -> List[str]:
    """
    Valida a sequência de passos do plano.
    Retorna lista de erros de segurança encontrados.

    Regra: Um passo crítico DEVE ter um human_checkpoint imediatamente antes.
    """
    errors: List[str] = []
    last_was_checkpoint = False

    for i, step in enumerate(steps):
        if is_absolutely_forbidden(step):
            errors.append(
                f"Passo {i + 1} ({step.action.value}): Ação absolutamente proibida detectada."
            )
            continue

        if step.action == ActionType.HUMAN_CHECKPOINT:
            last_was_checkpoint = True
            continue

        if is_critical_action(step) and not last_was_checkpoint:
            errors.append(
                f"Passo {i + 1} ({step.action.value}): Ação crítica sem human_checkpoint anterior."
            )
        else:
            # Reseta o flag após consumir o checkpoint
            last_was_checkpoint = False

    return errors


def check_step_safety(step: PlanStep, previous_was_checkpoint: bool) -> tuple[bool, str]:
    """
    Verifica se um único passo pode ser executado.
    Retorna (pode_executar: bool, motivo: str).
    """
    if is_absolutely_forbidden(step):
        reason = "Ação absolutamente proibida — bloqueio incondicional."
        log_blocked(str(step.action.value), reason)
        return False, reason

    if is_critical_action(step) and not previous_was_checkpoint:
        reason = (
            "Ação crítica detectada sem human_checkpoint anterior. "
            "Adicione um passo human_checkpoint antes desta ação no plano YAML."
        )
        log_blocked(str(step.action.value), reason)
        return False, reason

    return True, ""
