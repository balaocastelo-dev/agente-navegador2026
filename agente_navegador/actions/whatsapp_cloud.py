"""
Ações específicas para WhatsApp Cloud API.

Este módulo fornece helpers para configuração da WhatsApp Cloud API
via Meta Developers. NUNCA automatiza o registro de número ou envio de mensagens.

Referências oficiais:
    https://developers.facebook.com/docs/whatsapp/cloud-api/get-started
    https://developers.facebook.com/docs/whatsapp/cloud-api/phone-numbers
"""
from __future__ import annotations

from agente_navegador import browser as brw
from agente_navegador.logger import get_logger

log = get_logger(__name__)

WHATSAPP_GETTING_STARTED_URL = (
    "https://developers.facebook.com/docs/whatsapp/cloud-api/get-started"
)
WHATSAPP_SANDBOX_URL = "https://developers.facebook.com/apps/"


async def navigate_to_whatsapp_docs() -> str:
    """Navega para a documentação oficial da WhatsApp Cloud API."""
    await brw.safe_goto(WHATSAPP_GETTING_STARTED_URL)
    url = await brw.extract_current_url()
    log.info(f"WhatsApp Docs — URL: {url}")
    return url


async def navigate_to_whatsapp_setup(app_id: str = "") -> str:
    """
    Navega para a seção WhatsApp de um app Meta.
    app_id: ID do app Meta (fornecido pelo operador humano).
    """
    if app_id:
        url = f"https://developers.facebook.com/apps/{app_id}/whatsapp-business/wa-dev-console/"
        await brw.safe_goto(url)
    else:
        await brw.safe_goto(WHATSAPP_SANDBOX_URL)
    current = await brw.extract_current_url()
    log.info(f"WhatsApp Setup — URL: {current}")
    return current


async def collect_phone_number_id(selector: str) -> str:
    """
    Coleta o Phone Number ID (não registra nem conecta número real).
    ATENÇÃO: Registrar número é ação crítica — exige checkpoint humano.
    """
    try:
        value = await brw.collect_input_value(selector, timeout_ms=10000)
        log.info(f"Phone Number ID coletado: {value}")
        return value
    except Exception as e:
        log.warning(f"Não foi possível coletar Phone Number ID: {e}")
        return ""


async def collect_waba_id(selector: str) -> str:
    """
    Coleta o WhatsApp Business Account ID (WABA ID).
    """
    try:
        value = await brw.collect_input_value(selector, timeout_ms=10000)
        log.info(f"WABA ID coletado: {value}")
        return value
    except Exception as e:
        log.warning(f"Não foi possível coletar WABA ID: {e}")
        return ""
