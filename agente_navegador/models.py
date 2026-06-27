"""
Modelos Pydantic para validação dos planos YAML e estruturas de dados do agente.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ActionType(str, Enum):
    """Tipos de ação suportados pelo motor de execução."""
    GOTO = "goto"
    CLICK = "click"
    FILL = "fill"
    WAIT_FOR_SELECTOR = "wait_for_selector"
    EXTRACT_TEXT = "extract_text"
    EXTRACT_URL = "extract_url"
    SCREENSHOT = "screenshot"
    HUMAN_CHECKPOINT = "human_checkpoint"
    COLLECT_INPUT_VALUE = "collect_input_value"
    COLLECT_ATTRIBUTE = "collect_attribute"


class PlanStep(BaseModel):
    """Um passo dentro de um plano de execução."""
    action: ActionType
    # --- goto ---
    url: Optional[str] = None
    # --- click / wait_for_selector / collect_* ---
    selector: Optional[str] = None
    # --- fill ---
    value: Optional[str] = None
    # --- extract_* / collect_* ---
    save_as: Optional[str] = None
    # --- screenshot ---
    name: Optional[str] = None
    # --- human_checkpoint ---
    message: Optional[str] = None
    # --- collect_attribute ---
    attribute: Optional[str] = None
    # --- timeout override ---
    timeout_ms: Optional[int] = None
    # --- Dados extras livres ---
    extra: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError(f"URL inválida (deve começar com http:// ou https://): {v}")
        return v


class Plan(BaseModel):
    """Plano de execução completo carregado de um arquivo YAML."""
    name: str
    description: Optional[str] = ""
    version: Optional[str] = "1.0"
    steps: List[PlanStep] = Field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)

    @field_validator("steps", mode="before")
    @classmethod
    def steps_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("O plano deve ter pelo menos um passo (steps).")
        return v


class CollectedData(BaseModel):
    """Dados coletados durante a execução de um plano."""
    key: str
    value: str
    collected_at: str  # ISO timestamp
    plan_name: str


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_HUMAN = "waiting_human"
    FINISHED = "finished"
    ERROR = "error"
    BLOCKED = "blocked"


class RunResult(BaseModel):
    """Resultado de uma execução de plano."""
    plan_name: str
    status: AgentStatus
    steps_completed: int = 0
    steps_total: int = 0
    collected_data: List[CollectedData] = Field(default_factory=list)
    screenshots: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    blocked_actions: List[str] = Field(default_factory=list)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
