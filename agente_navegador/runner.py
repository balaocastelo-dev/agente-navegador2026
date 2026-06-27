"""
Motor de execução de planos — processa os passos de um Plan e coordena
browser, supervisor e segurança.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from agente_navegador import browser as brw
from agente_navegador.logger import get_logger, log_agent, log_success
from agente_navegador.models import (
    ActionType,
    AgentStatus,
    CollectedData,
    Plan,
    PlanStep,
    RunResult,
)
from agente_navegador.safety import check_step_safety, is_critical_action
from agente_navegador.supervisor import confirm_critical_action, human_checkpoint
from agente_navegador.actions.whatsapp_web import (
    wait_for_whatsapp_web_login,
    run_auto_reply_loop,
)

log = get_logger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PlanRunner:
    """Executa um plano passo a passo com supervisão humana."""

    def __init__(self, plan: Plan, headless: bool = False):
        self.plan = plan
        self.headless = headless
        self.result = RunResult(
            plan_name=plan.name,
            status=AgentStatus.IDLE,
            steps_total=len(plan.steps),
            started_at=_now_iso(),
        )
        self._previous_was_checkpoint = False

    async def run(self) -> RunResult:
        """Executa todos os passos do plano."""
        self.result.status = AgentStatus.RUNNING
        log_agent(f"Iniciando plano: '{self.plan.name}'")
        log.info(self.plan.description or "")

        try:
            await brw.start_browser(headless=self.headless)

            for i, step in enumerate(self.plan.steps):
                log_agent(f"Passo {i + 1}/{len(self.plan.steps)} — {step.action.value}")

                # Verificação de segurança em runtime
                can_run, reason = check_step_safety(step, self._previous_was_checkpoint)
                if not can_run:
                    self.result.blocked_actions.append(
                        f"Passo {i + 1} ({step.action.value}): {reason}"
                    )
                    self.result.status = AgentStatus.BLOCKED
                    log.error(f"Bloqueado: {reason}")
                    break

                # Executa o passo
                success = await self._execute_step(step, i + 1)
                if not success:
                    self.result.status = AgentStatus.ERROR
                    break

                self.result.steps_completed += 1

            else:
                # Todos os passos concluídos
                self.result.status = AgentStatus.FINISHED
                log_success(f"Plano '{self.plan.name}' concluído com sucesso!")

        except KeyboardInterrupt:
            log.warning("Execução interrompida pelo usuário (Ctrl+C).")
            self.result.status = AgentStatus.PAUSED
        except Exception as exc:
            log.exception(f"Erro inesperado durante execução: {exc}")
            self.result.errors.append(str(exc))
            self.result.status = AgentStatus.ERROR
        finally:
            await brw.stop_browser()
            self.result.finished_at = _now_iso()

        return self.result

    async def _execute_step(self, step: PlanStep, step_num: int) -> bool:
        """Executa um único passo. Retorna True em sucesso."""
        action = step.action
        timeout = step.timeout_ms

        try:
            if action == ActionType.GOTO:
                await brw.safe_goto(step.url, timeout_ms=timeout)

            elif action == ActionType.CLICK:
                await brw.safe_click(step.selector, timeout_ms=timeout)

            elif action == ActionType.FILL:
                await brw.safe_fill(step.selector, step.value or "", timeout_ms=timeout)

            elif action == ActionType.WAIT_FOR_SELECTOR:
                page = await brw.get_page()
                await page.wait_for_selector(
                    step.selector, timeout=timeout or 30000
                )

            elif action == ActionType.EXTRACT_TEXT:
                text = await brw.extract_text(step.selector, timeout_ms=timeout)
                if step.save_as:
                    self._save_collected(step.save_as, text)
                log.info(f"Texto extraído ({step.save_as or 'sem nome'}): {text[:100]}")

            elif action == ActionType.EXTRACT_URL:
                url = await brw.extract_current_url()
                if step.save_as:
                    self._save_collected(step.save_as, url)
                log.info(f"URL atual extraída: {url}")

            elif action == ActionType.SCREENSHOT:
                filepath = await brw.take_screenshot(step.name or f"step_{step_num}")
                self.result.screenshots.append(str(filepath))

            elif action == ActionType.HUMAN_CHECKPOINT:
                self.result.status = AgentStatus.WAITING_HUMAN
                confirmed = human_checkpoint(step.message or "Confirme para continuar.")
                self._previous_was_checkpoint = True
                if not confirmed:
                    log.warning("Operador cancelou no checkpoint — encerrando.")
                    self.result.status = AgentStatus.PAUSED
                    return False
                self.result.status = AgentStatus.RUNNING
                return True  # retorna cedo para manter _previous_was_checkpoint = True

            elif action == ActionType.COLLECT_INPUT_VALUE:
                value = await brw.collect_input_value(step.selector, timeout_ms=timeout)
                if step.save_as:
                    self._save_collected(step.save_as, value)
                log.info(f"Valor coletado ({step.save_as or ''}): {value}")

            elif action == ActionType.COLLECT_ATTRIBUTE:
                value = await brw.collect_attribute(
                    step.selector, step.attribute or "value", timeout_ms=timeout
                )
                if step.save_as:
                    self._save_collected(step.save_as, value)
                log.info(f"Atributo coletado ({step.attribute}={value})")

            elif action == ActionType.WHATSAPP_WEB_RESPONDER:
                message_text = step.value or (step.extra or {}).get("message_text") or "Olá! Recebemos sua mensagem no Balão da Informática Castelo."
                req_conf = (step.extra or {}).get("require_confirmation", True)
                max_cycles = (step.extra or {}).get("max_cycles", 5)
                delay_sec = (step.extra or {}).get("cycle_delay_sec", 5)

                # Aguarda o login inicial
                await wait_for_whatsapp_web_login()
                # Executa o loop de verificação e resposta
                replied_count = await run_auto_reply_loop(
                    message_template=message_text,
                    require_confirmation=req_conf,
                    max_cycles=max_cycles,
                    cycle_delay_sec=delay_sec,
                )
                if step.save_as:
                    self._save_collected(step.save_as, str(replied_count))

            # Reset do flag de checkpoint após ação não-checkpoint
            self._previous_was_checkpoint = False
            return True

        except Exception as exc:
            log.error(f"Erro no passo {step_num} ({action.value}): {exc}")
            self.result.errors.append(f"Passo {step_num}: {exc}")
            return False

    def _save_collected(self, key: str, value: str) -> None:
        """Salva um dado coletado no resultado."""
        entry = CollectedData(
            key=key,
            value=value,
            collected_at=_now_iso(),
            plan_name=self.plan.name,
        )
        self.result.collected_data.append(entry)
