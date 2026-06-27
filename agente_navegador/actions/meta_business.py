"""
Ações específicas para Meta Business Manager.

Este módulo fornece helpers de alto nível para os planos YAML relacionados
ao Meta Business. Todas as ações críticas exigem checkpoint humano.

Referências oficiais:
    https://business.facebook.com/
    https://developers.facebook.com/
    https://developers.facebook.com/docs/whatsapp/cloud-api
"""
from __future__ import annotations

from agente_navegador import browser as brw
from agente_navegador.logger import get_logger

log = get_logger(__name__)

META_BUSINESS_URL = "https://business.facebook.com/"
META_DEVELOPERS_URL = "https://developers.facebook.com/apps/"
META_GRAPH_EXPLORER_URL = "https://developers.facebook.com/tools/explorer/"


async def navigate_to_meta_business() -> str:
    """Navega para o Meta Business Manager e retorna a URL atual."""
    await brw.safe_goto(META_BUSINESS_URL)
    url = await brw.extract_current_url()
    log.info(f"Meta Business — URL atual: {url}")
    return url


async def navigate_to_meta_developers() -> str:
    """Navega para o portal Meta for Developers."""
    await brw.safe_goto(META_DEVELOPERS_URL)
    url = await brw.extract_current_url()
    log.info(f"Meta Developers — URL atual: {url}")
    return url


async def navigate_to_graph_explorer() -> str:
    """Navega para o Graph Explorer do Meta."""
    await brw.safe_goto(META_GRAPH_EXPLORER_URL)
    url = await brw.extract_current_url()
    log.info(f"Graph Explorer — URL atual: {url}")
    return url


async def screenshot_meta_home(name: str = "meta-business-home") -> str:
    """Tira screenshot do Meta Business e retorna o caminho."""
    filepath = await brw.take_screenshot(name)
    return str(filepath)


async def collect_app_id(selector: str = "input[name='app_id']") -> str:
    """
    Coleta o App ID da página de configurações do app Meta.
    NOTA: Navegue até a página do app antes de chamar esta função.
    """
    try:
        app_id = await brw.collect_input_value(selector, timeout_ms=10000)
        log.info(f"App ID coletado: {app_id}")
        return app_id
    except Exception:
        # Tenta via texto
        try:
            app_id = await brw.extract_text("[data-testid='app-id']", timeout_ms=5000)
            log.info(f"App ID coletado (texto): {app_id}")
            return app_id
        except Exception as e:
            log.warning(f"Não foi possível coletar App ID: {e}")
            return ""
