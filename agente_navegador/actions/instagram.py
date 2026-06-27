"""
Ações específicas para Instagram (conta profissional / Graph API).

Referências oficiais:
    https://business.instagram.com/
    https://developers.facebook.com/docs/instagram-api
    https://developers.facebook.com/docs/instagram-basic-display-api
"""
from __future__ import annotations

from agente_navegador import browser as brw
from agente_navegador.logger import get_logger

log = get_logger(__name__)

INSTAGRAM_BUSINESS_URL = "https://business.instagram.com/"
IG_DEVELOPERS_URL = "https://developers.facebook.com/docs/instagram-api"
IG_PROFILE_URL = "https://www.instagram.com/balaodainformatica_castelo/"


async def navigate_to_instagram_business() -> str:
    """Navega para o portal Instagram Business."""
    await brw.safe_goto(INSTAGRAM_BUSINESS_URL)
    url = await brw.extract_current_url()
    log.info(f"Instagram Business — URL: {url}")
    return url


async def navigate_to_instagram_profile() -> str:
    """Navega para o perfil Instagram da empresa."""
    await brw.safe_goto(IG_PROFILE_URL)
    url = await brw.extract_current_url()
    log.info(f"Perfil Instagram — URL: {url}")
    return url


async def navigate_to_instagram_docs() -> str:
    """Navega para a documentação da Instagram Graph API."""
    await brw.safe_goto(IG_DEVELOPERS_URL)
    url = await brw.extract_current_url()
    log.info(f"Instagram API Docs — URL: {url}")
    return url


async def collect_instagram_user_id(selector: str) -> str:
    """
    Coleta o Instagram User ID de um elemento na página.
    Este ID é necessário para a Graph API.
    """
    try:
        value = await brw.extract_text(selector, timeout_ms=10000)
        log.info(f"Instagram User ID coletado: {value}")
        return value
    except Exception as e:
        log.warning(f"Não foi possível coletar Instagram User ID: {e}")
        return ""
