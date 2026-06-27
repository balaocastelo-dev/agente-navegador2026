"""
Módulo de gerenciamento do navegador com Playwright.
Abre um perfil local separado e mantém o navegador visível (headed) por padrão.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from agente_navegador.config import config
from agente_navegador.logger import get_logger, log_agent

log = get_logger(__name__)

_playwright_instance: Optional[Playwright] = None
_browser: Optional[Browser] = None
_context: Optional[BrowserContext] = None
_page: Optional[Page] = None


async def start_browser(headless: Optional[bool] = None) -> Page:
    """
    Inicia o Chromium com um perfil persistente local.
    Sempre visible (headed) a menos que explicitamente definido como headless.
    """
    global _playwright_instance, _browser, _context, _page

    is_headless = headless if headless is not None else config.browser_headless

    log_agent(
        f"Iniciando navegador — modo: {'headless' if is_headless else 'headed (visível)'}"
    )
    log.info(f"Perfil do navegador: {config.browser_profile_dir}")

    _playwright_instance = await async_playwright().start()

    # Usar perfil persistente para manter sessões (sem salvar senhas)
    _context = await _playwright_instance.chromium.launch_persistent_context(
        user_data_dir=str(config.browser_profile_dir),
        headless=is_headless,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
        ],
        viewport={"width": 1280, "height": 800},
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
    )

    _page = _context.pages[0] if _context.pages else await _context.new_page()

    log.info("Navegador iniciado com sucesso.")
    return _page


async def get_page() -> Page:
    """Retorna a página ativa ou inicia o navegador."""
    global _page
    if _page is None or _page.is_closed():
        return await start_browser()
    return _page


async def stop_browser() -> None:
    """Fecha o navegador e libera recursos."""
    global _playwright_instance, _browser, _context, _page
    log_agent("Encerrando navegador...")
    if _context:
        await _context.close()
    if _playwright_instance:
        await _playwright_instance.stop()
    _page = None
    _context = None
    _browser = None
    _playwright_instance = None
    log.info("Navegador encerrado.")


async def take_screenshot(name: str = "screenshot") -> Path:
    """
    Tira um screenshot e salva em screenshots/ com timestamp.
    Retorna o caminho do arquivo salvo.
    """
    page = await get_page()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.png"
    filepath = config.screenshot_dir / filename
    await page.screenshot(path=str(filepath), full_page=True)
    log.info(f"Screenshot salvo: {filepath.name}")
    return filepath


async def safe_goto(url: str, timeout_ms: Optional[int] = None) -> None:
    """Navega para uma URL com tratamento de erros."""
    page = await get_page()
    t = timeout_ms or config.default_timeout_ms
    log.info(f"Navegando para: {url}")
    await page.goto(url, timeout=t, wait_until="domcontentloaded")


async def safe_click(selector: str, timeout_ms: Optional[int] = None) -> None:
    """Clica em um elemento com espera."""
    page = await get_page()
    t = timeout_ms or config.default_timeout_ms
    log.info(f"Clicando em: {selector}")
    await page.wait_for_selector(selector, timeout=t)
    await page.click(selector)


async def safe_fill(selector: str, value: str, timeout_ms: Optional[int] = None) -> None:
    """Preenche um campo de formulário."""
    page = await get_page()
    t = timeout_ms or config.default_timeout_ms
    log.info(f"Preenchendo campo: {selector}")
    await page.wait_for_selector(selector, timeout=t)
    await page.fill(selector, value)


async def extract_text(selector: str, timeout_ms: Optional[int] = None) -> str:
    """Extrai texto de um elemento."""
    page = await get_page()
    t = timeout_ms or config.default_timeout_ms
    await page.wait_for_selector(selector, timeout=t)
    text = await page.inner_text(selector)
    return text.strip()


async def extract_current_url() -> str:
    """Retorna a URL atual da página."""
    page = await get_page()
    return page.url


async def collect_input_value(selector: str, timeout_ms: Optional[int] = None) -> str:
    """Coleta o valor de um input."""
    page = await get_page()
    t = timeout_ms or config.default_timeout_ms
    await page.wait_for_selector(selector, timeout=t)
    value = await page.input_value(selector)
    return value


async def collect_attribute(
    selector: str, attribute: str, timeout_ms: Optional[int] = None
) -> str:
    """Coleta um atributo HTML de um elemento."""
    page = await get_page()
    t = timeout_ms or config.default_timeout_ms
    await page.wait_for_selector(selector, timeout=t)
    value = await page.get_attribute(selector, attribute) or ""
    return value
