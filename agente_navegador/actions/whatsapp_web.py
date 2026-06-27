"""
Acoes especificas para WhatsApp Web (autenticacao por QR Code).

Este modulo fornece helpers para monitorar novas mensagens e enviar respostas
automoticas de forma supervisionada e com simulacao de comportamento humano.
"""
from __future__ import annotations

import asyncio
import random
from agente_navegador import browser as brw
from agente_navegador.logger import get_logger, log_agent, log_success
from agente_navegador.supervisor import confirm_critical_action

log = get_logger(__name__)

# Seletores comuns do WhatsApp Web
CHAT_LIST_CONTAINER = "#pane-side, [data-testid='chat-list']"
QR_CODE_CANVAS = "canvas, [data-testid='qrcode']"
INPUT_TEXTBOX = "div[contenteditable='true'][role='textbox'], [data-testid='conversation-text-input']"
SEND_BUTTON = "[data-testid='compose-btn-send'], span[data-icon='send']"

# XPath robusto para encontrar linhas de chat com mensagens nao lidas
UNREAD_CHAT_XPATH = (
    "//div[@role='row' and ("
    ".//*[contains(@data-testid, 'unread-count') or contains(@data-testid, 'unread')] or "
    ".//span[contains(@aria-label, 'unread') or contains(@aria-label, 'não lida')] or "
    ".//*[contains(@class, 'unread')] or "
    ".//span[contains(@class, 'unread-count')]"
    ")]"
)

# Seletor para a ultima mensagem recebida (incoming) no chat aberto
LAST_INCOMING_MESSAGE = "div.message-in"
MESSAGE_TEXT_SELECTOR = ".selectable-text, span.selectable-text"


async def wait_for_whatsapp_web_login(timeout_ms: int = 60000) -> bool:
    """
    Aguarda o carregamento do painel principal do WhatsApp Web.
    Se o QR Code estiver visivel, avisa o operador.
    """
    page = await brw.get_page()
    log.info("Aguardando carregamento do WhatsApp Web...")
    
    try:
        # Tenta esperar pela lista de chats ou pelo QR Code
        await page.wait_for_selector(f"{CHAT_LIST_CONTAINER}, {QR_CODE_CANVAS}", timeout=timeout_ms)
        
        # Verifica se o QR Code esta visivel
        qr_visible = await page.locator(QR_CODE_CANVAS).is_visible()
        if qr_visible:
            log.warning("QR Code detectado! Aguardando operador escanear o codigo...")
            # Aguarda ate a lista de chats aparecer (o login foi concluido)
            await page.wait_for_selector(CHAT_LIST_CONTAINER, timeout=120000)
            log_success("Login realizado com sucesso via QR Code!")
            return True
        
        log_success("WhatsApp Web ja estava logado.")
        return True
    except Exception as e:
        log.error(f"Erro ou timeout ao aguardar login do WhatsApp Web: {e}")
        return False


async def run_auto_reply_loop(
    message_template: str,
    require_confirmation: bool = True,
    max_cycles: int = 5,
    cycle_delay_sec: int = 5
) -> int:
    """
    Executa o loop de verificacao e resposta automatica.
    Retorna o numero de mensagens respondidas.
    """
    page = await brw.get_page()
    replied_count = 0
    
    log_agent(f"Iniciando loop de auto-resposta (Max ciclos: {max_cycles}, Delay: {cycle_delay_sec}s)")
    
    for cycle in range(max_cycles):
        log.info(f"Ciclo {cycle + 1}/{max_cycles} - Verificando novas mensagens...")
        
        # Encontra chats nao lidos usando o XPath robusto
        unread_chats = page.locator(f"xpath={UNREAD_CHAT_XPATH}")
        count = await unread_chats.count()
        
        if count > 0:
            log.info(f"Encontrado(s) {count} chat(s) com mensagens nao lidas.")
            
            # Processa o primeiro chat nao lido
            chat = unread_chats.first
            
            # Tenta obter o nome do contato/grupo
            chat_title = "Contato Desconhecido"
            try:
                # Geralmente o titulo do chat fica em um span com title ou classe especifica
                title_el = chat.locator("span[title], [data-testid='chat-title']")
                if await title_el.count() > 0:
                    chat_title = await title_el.first.get_attribute("title") or await title_el.first.inner_text() or chat_title
            except Exception as e:
                log.debug(f"Nao foi possivel ler o nome do contato: {e}")
                
            log_agent(f"Abrindo chat de: '{chat_title}'")
            await chat.click()
            await asyncio.sleep(1.5) # Aguarda o chat abrir e renderizar
            
            # Tenta capturar a ultima mensagem recebida para logar
            last_msg_text = "(nao foi possivel ler o conteudo da mensagem)"
            try:
                incoming_msgs = page.locator(LAST_INCOMING_MESSAGE)
                if await incoming_msgs.count() > 0:
                    last_msg = incoming_msgs.last
                    text_el = last_msg.locator(MESSAGE_TEXT_SELECTOR)
                    if await text_el.count() > 0:
                        last_msg_text = await text_el.first.inner_text()
            except Exception as e:
                log.debug(f"Nao foi possivel ler a ultima mensagem recebida: {e}")
                
            log.info(f"Ultima mensagem recebida de '{chat_title}': '{last_msg_text}'")
            
            # Verifica se precisa de confirmacao do operador
            should_send = True
            if require_confirmation:
                should_send = confirm_critical_action(
                    f"Responder para '{chat_title}' com:\n'{message_template}'"
                )
                
            if should_send:
                # Foca no campo de entrada
                await page.wait_for_selector(INPUT_TEXTBOX, timeout=5000)
                input_field = page.locator(INPUT_TEXTBOX).first
                await input_field.click()
                await asyncio.sleep(0.5)
                
                # Simula digitacao humana com atrasos aleatorios entre os caracteres
                log.info(f"Digitando resposta para {chat_title}...")
                for char in message_template:
                    await input_field.press(char)
                    await asyncio.sleep(random.uniform(0.03, 0.08)) # 30ms a 80ms de delay
                    
                await asyncio.sleep(0.5)
                
                # Envia pressionando Enter ou clicando no botao de enviar
                await page.keyboard.press("Enter")
                log_success(f"Resposta enviada para '{chat_title}'!")
                replied_count += 1
            else:
                log.warning(f"Resposta para '{chat_title}' recusada pelo operador.")
                
            # Aguarda um momento antes de continuar
            await asyncio.sleep(2)
        else:
            log.info("Nenhuma nova mensagem encontrada.")
            
        await asyncio.sleep(cycle_delay_sec)
        
    log_agent(f"Loop de auto-resposta concluido. Total respondido: {replied_count}")
    return replied_count
