"""
Testes para o carregamento e validação de planos YAML.
"""
import textwrap
from pathlib import Path

import pytest
import yaml

from agente_navegador.collectors import load_plan, validate_plan
from agente_navegador.models import ActionType, Plan, PlanStep


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_plan_dir(tmp_path: Path) -> Path:
    """Cria um diretório temporário para planos de teste."""
    plans_dir = tmp_path / "plans"
    plans_dir.mkdir()
    return plans_dir


def write_plan(directory: Path, filename: str, content: str) -> Path:
    """Escreve um arquivo YAML de plano no diretório temporário."""
    plan_file = directory / filename
    plan_file.write_text(content, encoding="utf-8")
    return plan_file


# ---------------------------------------------------------------------------
# Planos YAML de teste
# ---------------------------------------------------------------------------

VALID_PLAN_YAML = textwrap.dedent("""
    name: test_plan
    description: Plano de teste básico
    version: "1.0"
    steps:
      - action: goto
        url: https://business.facebook.com/
      - action: screenshot
        name: home
      - action: extract_url
        save_as: current_url
""")

PLAN_WITH_CHECKPOINT_YAML = textwrap.dedent("""
    name: plan_with_checkpoint
    description: Plano com checkpoint humano
    steps:
      - action: goto
        url: https://business.facebook.com/
      - action: human_checkpoint
        message: Faça login manualmente.
      - action: screenshot
        name: after-login
      - action: extract_url
        save_as: url_after_login
""")

PLAN_MISSING_STEPS_YAML = textwrap.dedent("""
    name: plan_sem_steps
    description: Plano sem passos
    steps: []
""")

PLAN_INVALID_URL_YAML = textwrap.dedent("""
    name: plan_url_invalida
    description: Plano com URL inválida
    steps:
      - action: goto
        url: javascript:alert('xss')
""")

PLAN_INVALID_ACTION_YAML = textwrap.dedent("""
    name: plan_acao_invalida
    description: Plano com ação não suportada
    steps:
      - action: hack_system
        url: https://example.com
""")

REAL_META_PLAN_PATH = Path("plans/meta_whatsapp_setup.yaml")
REAL_INSTAGRAM_PLAN_PATH = Path("plans/instagram_setup.yaml")
REAL_FACEBOOK_PLAN_PATH = Path("plans/facebook_page_setup.yaml")
REAL_TIKTOK_PLAN_PATH = Path("plans/tiktok_developers_setup.yaml")


# ---------------------------------------------------------------------------
# Testes de carregamento
# ---------------------------------------------------------------------------

class TestLoadPlan:
    def test_load_valid_plan(self, tmp_plan_dir: Path):
        plan_file = write_plan(tmp_plan_dir, "valid.yaml", VALID_PLAN_YAML)
        plan = load_plan(plan_file)
        assert isinstance(plan, Plan)
        assert plan.name == "test_plan"
        assert len(plan.steps) == 3

    def test_load_plan_with_checkpoint(self, tmp_plan_dir: Path):
        plan_file = write_plan(tmp_plan_dir, "checkpoint.yaml", PLAN_WITH_CHECKPOINT_YAML)
        plan = load_plan(plan_file)
        assert plan.name == "plan_with_checkpoint"
        assert len(plan.steps) == 4
        # Verifica que o checkpoint está presente
        checkpoint_steps = [s for s in plan.steps if s.action == ActionType.HUMAN_CHECKPOINT]
        assert len(checkpoint_steps) == 1
        assert "login" in checkpoint_steps[0].message.lower()

    def test_load_nonexistent_plan(self, tmp_plan_dir: Path):
        with pytest.raises(FileNotFoundError):
            load_plan(tmp_plan_dir / "nao_existe.yaml")

    def test_load_plan_empty_steps_fails(self, tmp_plan_dir: Path):
        plan_file = write_plan(tmp_plan_dir, "empty.yaml", PLAN_MISSING_STEPS_YAML)
        with pytest.raises(ValueError, match="pelo menos um passo"):
            load_plan(plan_file)

    def test_load_plan_invalid_url_fails(self, tmp_plan_dir: Path):
        plan_file = write_plan(tmp_plan_dir, "invalid_url.yaml", PLAN_INVALID_URL_YAML)
        with pytest.raises(ValueError):
            load_plan(plan_file)

    def test_load_plan_invalid_action_fails(self, tmp_plan_dir: Path):
        plan_file = write_plan(tmp_plan_dir, "invalid_action.yaml", PLAN_INVALID_ACTION_YAML)
        with pytest.raises(ValueError):
            load_plan(plan_file)


# ---------------------------------------------------------------------------
# Testes de validação de segurança
# ---------------------------------------------------------------------------

class TestValidatePlan:
    def test_validate_valid_plan(self, tmp_plan_dir: Path):
        plan_file = write_plan(tmp_plan_dir, "valid.yaml", VALID_PLAN_YAML)
        valid, errors = validate_plan(plan_file)
        assert valid is True
        assert errors == []

    def test_validate_plan_with_checkpoint(self, tmp_plan_dir: Path):
        plan_file = write_plan(tmp_plan_dir, "checkpoint.yaml", PLAN_WITH_CHECKPOINT_YAML)
        valid, errors = validate_plan(plan_file)
        assert valid is True
        assert errors == []

    def test_validate_nonexistent_plan(self, tmp_plan_dir: Path):
        valid, errors = validate_plan(tmp_plan_dir / "fantasma.yaml")
        assert valid is False
        assert len(errors) > 0

    def test_validate_plan_critical_without_checkpoint(self, tmp_plan_dir: Path):
        content = textwrap.dedent("""
            name: plan_critico_sem_checkpoint
            description: Plano crítico sem checkpoint
            steps:
              - action: goto
                url: https://business.facebook.com/
              - action: fill
                selector: "#btn"
                value: publicar conteúdo
        """)
        plan_file = write_plan(tmp_plan_dir, "critical.yaml", content)
        valid, errors = validate_plan(plan_file)
        assert valid is False
        assert len(errors) > 0

    def test_validate_plan_critical_with_checkpoint_ok(self, tmp_plan_dir: Path):
        content = textwrap.dedent("""
            name: plan_critico_com_checkpoint
            description: Plano crítico com checkpoint correto
            steps:
              - action: goto
                url: https://business.facebook.com/
              - action: human_checkpoint
                message: Confirme para continuar com a publicação.
              - action: fill
                selector: "#btn"
                value: publicar conteúdo
        """)
        plan_file = write_plan(tmp_plan_dir, "critical_ok.yaml", content)
        valid, errors = validate_plan(plan_file)
        assert valid is True


# ---------------------------------------------------------------------------
# Testes de estrutura dos passos
# ---------------------------------------------------------------------------

class TestPlanStepStructure:
    def test_all_action_types_parseable(self, tmp_plan_dir: Path):
        """Verifica que todos os ActionTypes podem ser parseados do YAML."""
        for action_type in ActionType:
            data = {"action": action_type.value}
            # Adiciona campos obrigatórios mínimos por tipo
            if action_type == ActionType.GOTO:
                data["url"] = "https://example.com"
            elif action_type in (ActionType.CLICK, ActionType.WAIT_FOR_SELECTOR):
                data["selector"] = "#el"
            elif action_type == ActionType.FILL:
                data["selector"] = "#el"
                data["value"] = "texto"
            elif action_type in (ActionType.EXTRACT_TEXT, ActionType.COLLECT_INPUT_VALUE):
                data["selector"] = "#el"
            elif action_type == ActionType.COLLECT_ATTRIBUTE:
                data["selector"] = "#el"
                data["attribute"] = "href"
            step = PlanStep.model_validate(data)
            assert step.action == action_type

    def test_goto_requires_valid_http_url(self):
        with pytest.raises(Exception):
            PlanStep.model_validate({"action": "goto", "url": "ftp://invalid"})

    def test_screenshot_name_optional(self):
        step = PlanStep.model_validate({"action": "screenshot"})
        assert step.name is None

    def test_human_checkpoint_message_optional(self):
        step = PlanStep.model_validate({"action": "human_checkpoint"})
        assert step.message is None


# ---------------------------------------------------------------------------
# Testes com planos reais do projeto
# ---------------------------------------------------------------------------

class TestRealPlans:
    """Testa que os planos YAML reais do projeto são válidos."""

    @pytest.mark.skipif(
        not REAL_META_PLAN_PATH.exists(),
        reason="Arquivo plans/meta_whatsapp_setup.yaml não encontrado"
    )
    def test_meta_whatsapp_plan_valid(self):
        valid, errors = validate_plan(REAL_META_PLAN_PATH)
        assert valid is True, f"Plano inválido: {errors}"

    @pytest.mark.skipif(
        not REAL_INSTAGRAM_PLAN_PATH.exists(),
        reason="Arquivo plans/instagram_setup.yaml não encontrado"
    )
    def test_instagram_plan_valid(self):
        valid, errors = validate_plan(REAL_INSTAGRAM_PLAN_PATH)
        assert valid is True, f"Plano inválido: {errors}"

    @pytest.mark.skipif(
        not REAL_FACEBOOK_PLAN_PATH.exists(),
        reason="Arquivo plans/facebook_page_setup.yaml não encontrado"
    )
    def test_facebook_page_plan_valid(self):
        valid, errors = validate_plan(REAL_FACEBOOK_PLAN_PATH)
        assert valid is True, f"Plano inválido: {errors}"

    @pytest.mark.skipif(
        not REAL_TIKTOK_PLAN_PATH.exists(),
        reason="Arquivo plans/tiktok_developers_setup.yaml não encontrado"
    )
    def test_tiktok_plan_valid(self):
        valid, errors = validate_plan(REAL_TIKTOK_PLAN_PATH)
        assert valid is True, f"Plano inválido: {errors}"
