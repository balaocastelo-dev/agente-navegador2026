"""
Ações específicas para TikTok Developers / TikTok for Business.

Referências oficiais:
    https://developers.tiktok.com/
    https://developers.tiktok.com/doc/content-posting-api-get-started
    https://ads.tiktok.com/
"""
from __future__ import annotations

from agente_navegador import browser as brw
from agente_navegador.logger import get_logger

log = get_logger(__name__)

TIKTOK_DEVELOPERS_URL = "https://developers.tiktok.com/"
TIKTOK_APPS_URL = "https://developers.tiktok.com/apps/"
TIKTOK_DOCS_CONTENT_API = (
    "https://developers.tiktok.com/doc/content-posting-api-get-started"
)
TIKTOK_FOR_BUSINESS_URL = "https://ads.tiktok.com/"


async def navigate_to_tiktok_developers() -> str:
    """Navega para o portal TikTok Developers."""
    await brw.safe_goto(TIKTOK_DEVELOPERS_URL)
    url = await brw.extract_current_url()
    log.info(f"TikTok Developers — URL: {url}")
    return url


async def navigate_to_tiktok_apps() -> str:
    """Navega para o gerenciador de apps do TikTok Developers."""
    await brw.safe_goto(TIKTOK_APPS_URL)
    url = await brw.extract_current_url()
    log.info(f"TikTok Apps — URL: {url}")
    return url


async def navigate_to_content_posting_docs() -> str:
    """Navega para a documentação da Content Posting API."""
    await brw.safe_goto(TIKTOK_DOCS_CONTENT_API)
    url = await brw.extract_current_url()
    log.info(f"TikTok Content API Docs — URL: {url}")
    return url


async def collect_tiktok_app_id(selector: str) -> str:
    """
    Coleta o App ID/Client Key do TikTok.
    ATENÇÃO: Não coleta Client Secret sem checkpoint humano.
    """
    try:
        value = await brw.collect_input_value(selector, timeout_ms=10000)
        log.info(f"TikTok App ID coletado: {value}")
        return value
    except Exception as e:
        log.warning(f"Não foi possível coletar TikTok App ID: {e}")
        return ""


async def screenshot_tiktok_app(name: str = "tiktok-app") -> str:
    """Tira screenshot da configuração do app TikTok."""
    filepath = await brw.take_screenshot(name)
    return str(filepath)
