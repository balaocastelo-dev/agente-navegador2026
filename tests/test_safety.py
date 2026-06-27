"""
Testes para o módulo de segurança (safety.py).
"""
import pytest

from agente_navegador.models import ActionType, PlanStep
from agente_navegador.safety import (
    ABSOLUTELY_FORBIDDEN,
    CRITICAL_KEYWORDS,
    check_step_safety,
    is_absolutely_forbidden,
    is_critical_action,
    validate_plan_safety,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_step(action: ActionType, **kwargs) -> PlanStep:
    return PlanStep(action=action, **kwargs)


# ---------------------------------------------------------------------------
# is_critical_action
# ---------------------------------------------------------------------------

class TestIsCriticalAction:
    def test_goto_normal_url_not_critical(self):
        step = make_step(ActionType.GOTO, url="https://business.facebook.com/")
        assert is_critical_action(step) is False

    def test_fill_with_publish_keyword_is_critical(self):
        step = make_step(ActionType.FILL, selector="#btn", value="publicar")
        assert is_critical_action(step) is True

    def test_fill_with_send_keyword_is_critical(self):
        step = make_step(ActionType.FILL, selector="#msg", value="enviar mensagem")
        assert is_critical_action(step) is True

    def test_checkpoint_message_with_critical_keyword(self):
        step = make_step(
            ActionType.HUMAN_CHECKPOINT,
            message="Clique em aceitar termos antes de continuar",
        )
        assert is_critical_action(step) is True

    def test_screenshot_not_critical(self):
        step = make_step(ActionType.SCREENSHOT, name="home-screenshot")
        assert is_critical_action(step) is False

    def test_extract_url_not_critical(self):
        step = make_step(ActionType.EXTRACT_URL, save_as="current_url")
        assert is_critical_action(step) is False

    def test_fill_with_delete_keyword_is_critical(self):
        step = make_step(ActionType.FILL, selector="#action", value="excluir app")
        assert is_critical_action(step) is True

    def test_fill_with_token_keyword_is_critical(self):
        step = make_step(ActionType.FILL, selector="#token", value="gerar token permanente")
        assert is_critical_action(step) is True


# ---------------------------------------------------------------------------
# is_absolutely_forbidden
# ---------------------------------------------------------------------------

class TestIsAbsolutelyForbidden:
    def test_spam_is_forbidden(self):
        step = make_step(ActionType.FILL, selector="#msg", value="spam")
        assert is_absolutely_forbidden(step) is True

    def test_mass_message_is_forbidden(self):
        step = make_step(ActionType.FILL, selector="#action", value="disparo em massa")
        assert is_absolutely_forbidden(step) is True

    def test_normal_action_not_forbidden(self):
        step = make_step(ActionType.GOTO, url="https://developers.facebook.com/")
        assert is_absolutely_forbidden(step) is False

    def test_screenshot_not_forbidden(self):
        step = make_step(ActionType.SCREENSHOT, name="captura")
        assert is_absolutely_forbidden(step) is False


# ---------------------------------------------------------------------------
# check_step_safety
# ---------------------------------------------------------------------------

class TestCheckStepSafety:
    def test_normal_step_allowed(self):
        step = make_step(ActionType.GOTO, url="https://business.facebook.com/")
        ok, reason = check_step_safety(step, previous_was_checkpoint=False)
        assert ok is True
        assert reason == ""

    def test_critical_step_without_checkpoint_blocked(self):
        step = make_step(ActionType.FILL, selector="#btn", value="publicar conteúdo")
        ok, reason = check_step_safety(step, previous_was_checkpoint=False)
        assert ok is False
        assert "crítica" in reason.lower() or "critical" in reason.lower() or "checkpoint" in reason.lower()

    def test_critical_step_with_checkpoint_allowed(self):
        step = make_step(ActionType.FILL, selector="#btn", value="publicar conteúdo")
        ok, reason = check_step_safety(step, previous_was_checkpoint=True)
        assert ok is True

    def test_absolutely_forbidden_blocked_even_with_checkpoint(self):
        step = make_step(ActionType.FILL, selector="#msg", value="spam")
        ok, reason = check_step_safety(step, previous_was_checkpoint=True)
        assert ok is False


# ---------------------------------------------------------------------------
# validate_plan_safety
# ---------------------------------------------------------------------------

class TestValidatePlanSafety:
    def test_valid_plan_no_errors(self):
        steps = [
            make_step(ActionType.GOTO, url="https://business.facebook.com/"),
            make_step(ActionType.SCREENSHOT, name="home"),
            make_step(ActionType.EXTRACT_URL, save_as="url"),
        ]
        errors = validate_plan_safety(steps)
        assert errors == []

    def test_critical_without_checkpoint_raises_error(self):
        steps = [
            make_step(ActionType.GOTO, url="https://business.facebook.com/"),
            make_step(ActionType.FILL, selector="#btn", value="publicar conteúdo"),
        ]
        errors = validate_plan_safety(steps)
        assert len(errors) > 0

    def test_critical_with_checkpoint_before_ok(self):
        steps = [
            make_step(ActionType.GOTO, url="https://business.facebook.com/"),
            make_step(ActionType.HUMAN_CHECKPOINT, message="Confirme para continuar."),
            make_step(ActionType.FILL, selector="#btn", value="publicar conteúdo"),
        ]
        errors = validate_plan_safety(steps)
        assert errors == []

    def test_forbidden_always_raises_error(self):
        steps = [
            make_step(ActionType.HUMAN_CHECKPOINT, message="Confirme."),
            make_step(ActionType.FILL, selector="#msg", value="disparo em massa"),
        ]
        errors = validate_plan_safety(steps)
        assert len(errors) > 0

    def test_multiple_critical_steps_need_multiple_checkpoints(self):
        steps = [
            make_step(ActionType.HUMAN_CHECKPOINT, message="Checkpoint 1"),
            make_step(ActionType.FILL, selector="#a", value="publicar conteúdo"),
            # Falta checkpoint antes desta segunda ação crítica
            make_step(ActionType.FILL, selector="#b", value="enviar mensagem"),
        ]
        errors = validate_plan_safety(steps)
        assert len(errors) > 0

    def test_checkpoint_resets_between_critical_steps(self):
        steps = [
            make_step(ActionType.HUMAN_CHECKPOINT, message="Checkpoint 1"),
            make_step(ActionType.FILL, selector="#a", value="publicar conteúdo"),
            make_step(ActionType.HUMAN_CHECKPOINT, message="Checkpoint 2"),
            make_step(ActionType.FILL, selector="#b", value="enviar mensagem"),
        ]
        errors = validate_plan_safety(steps)
        assert errors == []
