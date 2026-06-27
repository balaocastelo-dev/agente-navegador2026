"""
Ações específicas para Facebook Page (Página do Facebook).

Referências oficiais:
    https://www.facebook.com/pages/create
    https://developers.facebook.com/docs/pages-api
    https://business.facebook.com/
"""
from __future__ import annotations

from agente_navegador import browser as brw
from agente_navegador.logger import get_logger

log = get_logger(__name__)

FACEBOOK_PAGES_URL = "https://www.facebook.com/pages/"
FACEBOOK_BUSINESS_URL = "https://business.facebook.com/"
PAGES_MANAGER_URL = "https://www.facebook.com/bookmarks/pages"


async def navigate_to_pages_manager() -> str:
    """Navega para o gerenciador de páginas do Facebook."""
    await brw.safe_goto(PAGES_MANAGER_URL)
    url = await brw.extract_current_url()
    log.info(f"Pages Manager — URL: {url}")
    return url


async def navigate_to_page(page_username: str) -> str:
    """Navega para uma Página específica do Facebook."""
    url = f"https://www.facebook.com/{page_username}"
    await brw.safe_goto(url)
    current = await brw.extract_current_url()
    log.info(f"Página Facebook — URL: {current}")
    return current


async def collect_page_id(selector: str = "meta[property='al:android:url']") -> str:
    """
    Tenta coletar o Page ID de elementos meta da página.
    """
    try:
        page_id = await brw.collect_attribute(selector, "content", timeout_ms=10000)
        # Extrai o ID numérico do URL (ex: fb://page/?id=1234567890)
        if "id=" in page_id:
            page_id = page_id.split("id=")[-1].split("&")[0]
        log.info(f"Page ID coletado: {page_id}")
        return page_id
    except Exception as e:
        log.warning(f"Não foi possível coletar Page ID via meta tag: {e}")
        return ""


async def collect_page_name(selector: str = "h1") -> str:
    """Coleta o nome da Página."""
    try:
        name = await brw.extract_text(selector, timeout_ms=10000)
        log.info(f"Nome da Página coletado: {name}")
        return name
    except Exception as e:
        log.warning(f"Não foi possível coletar nome da Página: {e}")
        return ""
