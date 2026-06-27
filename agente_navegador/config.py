"""
Módulo de configuração — carrega variáveis de ambiente e definições do projeto.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Carrega o .env da raiz do projeto
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


class Config(BaseModel):
    """Configurações globais do Agente Navegador."""

    # --- Navegador ---
    browser_headless: bool = Field(
        default_factory=lambda: os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
    )
    browser_profile_dir: Path = Field(
        default_factory=lambda: _ROOT / os.getenv("BROWSER_PROFILE_DIR", "browser-profile")
    )
    default_timeout_ms: int = Field(
        default_factory=lambda: int(os.getenv("DEFAULT_TIMEOUT_MS", "30000"))
    )

    # --- Diretórios ---
    screenshot_dir: Path = Field(
        default_factory=lambda: _ROOT / os.getenv("SCREENSHOT_DIR", "screenshots")
    )
    log_dir: Path = Field(
        default_factory=lambda: _ROOT / os.getenv("LOG_DIR", "logs")
    )
    plans_dir: Path = Field(default_factory=lambda: _ROOT / "plans")

    # --- Segurança ---
    require_confirmation: bool = Field(
        default_factory=lambda: os.getenv("REQUIRE_CONFIRMATION", "true").lower() == "true"
    )

    # --- Empresa ---
    company_name: str = "Balão da Informática Castelo"
    company_address: str = "Av. Anchieta, 789 – Campinas/SP"
    company_whatsapp: str = "(19) 98751-0267"
    company_phone: str = "(19) 3255-1661"
    company_instagram: str = "@balaodainformatica_castelo"
    company_site: str = "www.balao.info"

    class Config:
        arbitrary_types_allowed = True

    def ensure_dirs(self) -> None:
        """Garante que os diretórios necessários existem."""
        for d in [self.screenshot_dir, self.log_dir, self.browser_profile_dir]:
            d.mkdir(parents=True, exist_ok=True)


# Instância global
config = Config()
config.ensure_dirs()
