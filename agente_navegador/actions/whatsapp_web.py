"""
Acoes especificas para WhatsApp Web (autenticacao por QR Code).

Este modulo fornece helpers para monitorar novas mensagens e enviar respostas
automoticas de forma supervisionada, integrando buscas no site oficial
www.balao.info, dados do perfil institucional e consulta direta no Supabase.
"""
from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, List

from agente_navegador import browser as brw
from agente_navegador.actions.company_profile import get_company_info, scrape_company_info
from agente_navegador.logger import get_logger, log_agent, log_success
from agente_navegador.supervisor import confirm_critical_action
from agente_navegador.actions.gemini_responder import (
    generate_smart_response,
    classify_follow_up_intent,
    analyze_message_intent_and_keyword,
    generate_friendly_no_products_response,
    generate_general_gemini_response
)

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
LAST_INCOMING_MESSAGE = "div.message-in, div.x1cy8zhl"
MESSAGE_TEXT_SELECTOR = ".selectable-text, span.selectable-text, span[data-testid='selectable-text']"

# Estado global simples para controle via API
_selected_chat_name: str | None = None

# Sessões de busca de produtos por chat para paginação
_chat_sessions: dict[str, dict] = {}


def select_target_chat(chat_name: str | None) -> None:
    """Define qual contato o operador deseja responder/monitorar."""
    global _selected_chat_name
    _selected_chat_name = chat_name
    log.info(f"Contato selecionado via painel: {chat_name}")


async def get_active_chats() -> List[Dict[str, Any]]:
    """
    Retorna a lista de chats visiveis no WhatsApp Web para exibicao no painel.
    """
    try:
        page = await brw.get_page()
        # Garante que a lista de chats esta visivel
        await page.wait_for_selector(CHAT_LIST_CONTAINER, timeout=5000)
        
        chats = await page.evaluate("""
            () => {
                const results = [];
                const rows = document.querySelectorAll('div[role="row"]');
                rows.forEach((row, index) => {
                    // Tenta pegar o nome/titulo do contato
                    const titleEl = row.querySelector('span[title], [data-testid="chat-title"]');
                    if (!titleEl) return;
                    const name = titleEl.getAttribute('title') || titleEl.innerText || 'Desconhecido';
                    
                    // Tenta pegar a ultima mensagem
                    const msgEl = row.querySelector('span[data-testid="last-message"], [data-testid="last-msg-status"] + span');
                    const lastMessage = msgEl ? msgEl.innerText.trim() : '';
                    
                    // Verifica se tem nao lida e a contagem
                    const unreadEl = row.querySelector('[data-testid="icon-unread-count"], [data-testid="unread-count"], span[class*="unread"]');
                    const unread = !!unreadEl;
                    const unreadCount = unreadEl ? parseInt(unreadEl.innerText) || 1 : 0;
                    
                    results.push({
                        index,
                        name,
                        lastMessage,
                        unread,
                        unreadCount
                    });
                });
                return results;
            }
        """)
        return chats
    except Exception as e:
        log.debug(f"Nao foi possivel obter chats do WhatsApp Web: {e}")
        return []


async def select_chat_by_name(chat_name: str) -> bool:
    """
    Clica no chat com o nome especificado para foca-lo.
    """
    try:
        page = await brw.get_page()
        # Escapa aspas para o seletor XPath ou texto
        escaped_name = chat_name.replace('"', '\\"')
        
        # Encontra o chat na lista e clica
        chat_locator = page.locator(
            f'span[title="{escaped_name}"], [data-testid="chat-title"]:has-text("{chat_name}")'
        ).first
        
        if await chat_locator.count() > 0:
            await chat_locator.click()
            await asyncio.sleep(1.5)
            log_success(f"Chat selecionado: '{chat_name}'")
            return True
        else:
            log.warning(f"Chat '{chat_name}' nao encontrado na lista visivel.")
            return False
    except Exception as e:
        log.error(f"Erro ao selecionar chat '{chat_name}': {e}")
        return False


async def wait_for_whatsapp_web_login(timeout_ms: int = 60000) -> bool:
    """
    Aguarda o carregamento do painel principal do WhatsApp Web.
    Se o QR Code estiver visivel, avisa o operador.
    """
    page = await brw.get_page()
    log.info("Aguardando carregamento do WhatsApp Web...")
    
    try:
        await page.wait_for_selector(f"{CHAT_LIST_CONTAINER}, {QR_CODE_CANVAS}", timeout=timeout_ms)
        qr_visible = await page.locator(QR_CODE_CANVAS).is_visible()
        if qr_visible:
            log.warning("QR Code detectado! Aguardando operador escanear o codigo...")
            await page.wait_for_selector(CHAT_LIST_CONTAINER, timeout=120000)
            log_success("Login realizado com sucesso via QR Code!")
            
            # Aproveita o login para raspar info da empresa pela primeira vez
            await scrape_company_info(page)
            return True
        
        log_success("WhatsApp Web ja estava logado.")
        return True
    except Exception as e:
        log.error(f"Erro ou timeout ao aguardar login do WhatsApp Web: {e}")
        return False


def extract_search_term(message: str) -> str | None:
    """
    Detecta se o usuario esta perguntando por produtos e extrai o termo de busca.
    """
    msg = message.lower().strip()
    intent_keywords = [
        "preço", "preco", "quanto custa", "valor", "tem", "têm", "disponível", "disponivel",
        "comprar", "gostaria de saber", "qual o preço", "qual o preco", "quanto tá", "quanto ta"
    ]
    is_product_query = any(kw in msg for kw in intent_keywords)
    
    product_keywords = [
        "computador", "pc", "gamer", "notebook", "apple", "iphone", "ipad", "macbook",
        "teclado", "mouse", "monitor", "headset", "fone", "cadeira", "ssd", "hd", "placa",
        "memoria", "ram", "cooler", "fonte", "gabinete", "processador"
    ]
    has_product = any(prod in msg for prod in product_keywords)
    
    if not (is_product_query or has_product):
        return None

    cleaned = msg
    for phrase in intent_keywords:
        cleaned = cleaned.replace(phrase, "")
    for word in ["olá", "ola", "bom dia", "boa tarde", "boa noite", "por favor", "vocês", "voces"]:
        cleaned = cleaned.replace(word, "")
        
    cleaned = cleaned.strip("? .! \n\t,;*")
    
    if len(cleaned) >= 2:
        return cleaned
    
    for prod in product_keywords:
        if prod in msg:
            return prod
            
    return "computador"


def get_answer_from_company_profile(message: str) -> str | None:
    """
    Tenta responder perguntas institucionais com base nos dados do balao.info.
    """
    msg = message.lower().strip()
    info = get_company_info()
    
    address_keys = ["onde fica", "endereço", "endereco", "localização", "localizacao", "onde vcs ficam", "onde voces ficam", "onde fica a loja"]
    hours_keys = ["horário", "horario", "funciona", "abre", "fecha", "atendimento", "aberto"]
    contact_keys = ["telefone", "zap", "contato", "whats", "whatsapp", "email", "e-mail", "site"]
    
    if any(k in msg for k in address_keys):
        return f"Nossa loja fica na {info['address']}. Esperamos sua visita! 📍"
        
    if any(k in msg for k in hours_keys):
        return f"Nosso horario de funcionamento é: {info['hours']}. ⏰"
        
    if any(k in msg for k in contact_keys):
        return (
            f"Voce pode falar conosco pelo telefone {info['phone']} "
            f"ou pelo WhatsApp {info['whatsapp']}. Nosso email e: {info['email']}. 📞"
        )
        
    if any(k in msg for k in ["quem são", "quem sao", "loja", "sobre"]):
        return f"Somos o {info['name']}. {info['description']} Nosso endereço e {info['address']}. 🚀"
        
    return None


async def search_products_on_balao(page, search_term: str) -> list[dict[str, str]]:
    """
    Abre uma nova aba, pesquisa o termo no balao.info e extrai as ofertas.
    """
    log.info(f"Pesquisando '{search_term}' no site balao.info...")
    try:
        new_page = await page.context.new_page()
        url = f"https://www.balao.info/?search={search_term}"
        await new_page.goto(url, wait_until="domcontentloaded")
        await new_page.wait_for_timeout(3000)
        
        products = await new_page.evaluate("""
            () => {
                const results = [];
                const anchors = document.querySelectorAll('a');
                for (const a of anchors) {
                    if (a.href && a.href.includes('/product/')) {
                        const text = a.innerText.trim();
                        if (text.includes('R$')) {
                            const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                            let name = lines[0];
                            if (lines.length > 1 && lines[0] === lines[0].toUpperCase() && lines[0].length < 25) {
                                name = lines[1];
                            }
                            const priceMatch = text.match(/R\\$\\s*[\\d.,]+/);
                            const price = priceMatch ? priceMatch[0] : "Sob consulta";
                            if (!results.some(r => r.link === a.href)) {
                                results.push({
                                    name: name,
                                    price: price,
                                    link: a.href
                                });
                            }
                        }
                    }
                }
                return results;
            }
        """)
        await new_page.close()
        log.info(f"Encontrados {len(products)} produtos para '{search_term}'.")
        return products[:3]
    except Exception as e:
        log.error(f"Erro ao pesquisar produtos no balao.info: {e}")
        return []


async def consult_supabase_source(page) -> None:
    """
    Abre o Supabase em uma nova aba para consulta.
    """
    log_agent("Navegando para o Supabase (fonte de dados)...")
    try:
        new_page = await page.context.new_page()
        await new_page.goto("https://ptqqvezawobgnheesgvh.supabase.co")
        log_success("Aba do Supabase aberta com sucesso. Se necessario, realize o login.")
        await new_page.wait_for_timeout(10000)
    except Exception as e:
        log.error(f"Erro ao abrir Supabase: {e}")


async def get_message_id(msg_locator) -> str | None:
    """Extrai o atributo data-id do elemento ou de seus ancestrais/descendentes."""
    try:
        # 1. Tenta obter diretamente do elemento
        msg_id = await msg_locator.get_attribute("data-id")
        if msg_id:
            return msg_id
            
        # 2. Tenta obter de algum descendente
        descendant = msg_locator.locator("div[data-id], [data-id]")
        if await descendant.count() > 0:
            return await descendant.first.get_attribute("data-id")
            
        # 3. Tenta buscar nos ancestrais usando JavaScript na pagina
        msg_id = await msg_locator.evaluate("""el => {
            let current = el;
            while (current) {
                if (current.hasAttribute('data-id')) {
                    return current.getAttribute('data-id');
                }
                current = current.parentElement;
            }
            return null;
        }""")
        return msg_id
    except Exception as e:
        log.debug(f"Nao foi possivel extrair data-id da mensagem: {e}")
        return None


async def get_conversation_history(page) -> list[dict]:
    """
    Recupera o histórico recente das últimas 15 mensagens (remetente e texto) da conversa aberta.
    Identifica o remetente usando o prefixo do data-id do WhatsApp Web:
    - true_ -> Agente
    - false_ -> Cliente
    """
    try:
        history = await page.evaluate("""() => {
            const rows = Array.from(document.querySelectorAll('div[data-id]'));
            const results = [];
            for (const row of rows) {
                const dataId = row.getAttribute('data-id');
                if (!dataId) continue;
                
                let sender = null;
                if (dataId.startsWith('true_')) {
                    sender = 'Agente';
                } else if (dataId.startsWith('false_')) {
                    sender = 'Cliente';
                } else {
                    continue;
                }
                
                const textEl = row.querySelector('.selectable-text, span[data-testid="selectable-text"]');
                if (textEl) {
                    results.push({
                        sender: sender,
                        text: textEl.innerText.trim()
                    });
                }
            }
            return results.slice(-15);
        }""")
        return history
    except Exception as e:
        log.error(f"Erro ao recuperar historico de conversa: {e}")
        return []


def parse_price(price_str: str) -> float:
    """Converte string de preço (ex: 'R$ 1.717,43') para float."""
    clean = price_str.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(clean)
    except ValueError:
        return 999999.0


async def send_message_to_chat(page, text: str, delay_before_send_sec: float = 0.0) -> None:
    """Insere o texto de forma instantanea e digita o link lentamente, esperando o preview carregar."""
    await page.wait_for_selector(INPUT_TEXTBOX, timeout=5000)
    input_field = page.locator(INPUT_TEXTBOX).first
    await input_field.click()
    await asyncio.sleep(0.5)
    
    # Identifica se há um link na mensagem
    url_start = text.find("http://")
    if url_start == -1:
        url_start = text.find("https://")
        
    if url_start != -1 and delay_before_send_sec > 0:
        # Separa o texto antes do link e o próprio link
        text_before_link = text[:url_start]
        link = text[url_start:]
        
        # Insere o texto inicial instantaneamente
        await page.keyboard.insert_text(text_before_link)
        await asyncio.sleep(0.5)
        
        # Digita o link lentamente/caractere por caractere
        log.info("Simulando digitação humana para o link do produto...")
        for char in link:
            await page.keyboard.press(char)
            await asyncio.sleep(random.uniform(0.01, 0.03))
            
        # Espera um tempo randômico de 7 segundos para carregar o preview
        wait_time = random.uniform(7.0, 7.5)
        log.info(f"Aguardando {wait_time:.2f}s para o WhatsApp Web carregar o preview do link...")
        await asyncio.sleep(wait_time)
    else:
        # Sem link, insere tudo instantaneamente
        await page.keyboard.insert_text(text)
        
    await page.keyboard.press("Enter")
    await asyncio.sleep(1.0)


async def confirm_and_send_text(page, text: str, require_confirmation: bool, chat_title: str, delay: float = 0.0) -> bool:
    """Wrapper para confirmacao critica e envio de mensagem."""
    should_send = True
    if require_confirmation:
        should_send = confirm_critical_action(
            f"Enviar para '{chat_title}':\n\n{text}"
        )
    if should_send:
        await send_message_to_chat(page, text, delay_before_send_sec=delay)
        return True
    else:
        log.warning(f"Mensagem para '{chat_title}' recusada pelo operador.")
        return False


async def show_next_options(page, chat_title: str, require_confirmation: bool) -> None:
    """Exibe as próximas 3 opções da busca e pergunta sobre mais caras/baratas."""
    session = _chat_sessions.get(chat_title)
    if not session:
        return
        
    products = session["products"]
    idx = session["current_index"]
    
    to_show = products[idx:idx+3]
    if not to_show:
        msg = "Essas sao todas as opcoes que encontramos no momento! Deseja pesquisar outro produto?"
        await confirm_and_send_text(page, msg, require_confirmation, chat_title)
        return
        
    log.info(f"Mostrando {len(to_show)} produtos para '{chat_title}'...")
    for p in to_show:
        product_text = (
            f"📦 *{p['title']}*\n"
            f"💰 Preço: {p['price']}\n"
            f"🔗 Link: {p['link']}"
        )
        # Sempre espera 3 segundos após digitar o link do produto para o preview carregar
        await confirm_and_send_text(page, product_text, require_confirmation, chat_title, delay=3.0)
        
    session["current_index"] = idx + len(to_show)
    session["last_direction"] = "forward"
    
    follow_up = "Gostaria de ver opcoes mais baratas ou mais caras que essas que te mostrei?"
    await confirm_and_send_text(page, follow_up, require_confirmation, chat_title)


async def show_cheaper_options(page, chat_title: str, require_confirmation: bool) -> None:
    """Volta na lista ordenada para mostrar opções mais baratas."""
    session = _chat_sessions.get(chat_title)
    if not session:
        return
        
    products = session["products"]
    idx = session["current_index"]
    
    new_idx = idx - 6
    if new_idx < 0:
        msg = "Essas que te mostrei no inicio ja sao as nossas opcoes mais baratas em estoque! Gostaria de ver opcoes mais caras?"
        await confirm_and_send_text(page, msg, require_confirmation, chat_title)
        return
        
    to_show = products[new_idx:new_idx+3]
    log.info(f"Mostrando {len(to_show)} produtos mais baratos para '{chat_title}'...")
    for p in to_show:
        product_text = (
            f"📦 *{p['title']}*\n"
            f"💰 Preço: {p['price']}\n"
            f"🔗 Link: {p['link']}"
        )
        await confirm_and_send_text(page, product_text, require_confirmation, chat_title, delay=3.0)
        
    session["current_index"] = new_idx + len(to_show)
    session["last_direction"] = "backward"
    
    follow_up = "Gostaria de ver opcoes mais baratas ou mais caras que essas?"
    await confirm_and_send_text(page, follow_up, require_confirmation, chat_title)


async def show_expensive_options(page, chat_title: str, require_confirmation: bool) -> None:
    """Mostra opções mais caras (próximas na lista ordenada)."""
    session = _chat_sessions.get(chat_title)
    if not session:
        return
        
    products = session["products"]
    idx = session["current_index"]
    
    to_show = products[idx:idx+3]
    if not to_show:
        msg = "Ja te mostrei todas as opcoes mais caras disponiveis. Deseja pesquisar outro produto?"
        await confirm_and_send_text(page, msg, require_confirmation, chat_title)
        return
        
    log.info(f"Mostrando {len(to_show)} produtos mais caros para '{chat_title}'...")
    for p in to_show:
        product_text = (
            f"📦 *{p['title']}*\n"
            f"💰 Preço: {p['price']}\n"
            f"🔗 Link: {p['link']}"
        )
        await confirm_and_send_text(page, product_text, require_confirmation, chat_title, delay=3.0)
        
    session["current_index"] = idx + len(to_show)
    session["last_direction"] = "forward"
    
    follow_up = "Gostaria de ver opcoes mais baratas ou mais caras que essas?"
    await confirm_and_send_text(page, follow_up, require_confirmation, chat_title)


async def handle_whatsapp_message_flow(page, user_message: str, history: list[dict], require_confirmation: bool, chat_title: str) -> None:
    """Coordena o fluxo inteligente de respostas e paginação de busca."""
    session = _chat_sessions.get(chat_title)
    
    if session and "products" in session and session["products"]:
        decision = await classify_follow_up_intent(user_message, history)
        log.info(f"Classificacao do follow up para '{chat_title}': {decision}")
        
        if decision == "CHEAPER":
            await show_cheaper_options(page, chat_title, require_confirmation)
            return
        elif decision == "EXPENSIVE":
            await show_expensive_options(page, chat_title, require_confirmation)
            return
        elif decision == "NEW_SEARCH":
            # Reseta a busca antiga para iniciar nova busca
            _chat_sessions.pop(chat_title, None)
            
    # Nova busca ou dúvida geral
    intent_data = await analyze_message_intent_and_keyword(user_message, history)
    log.info(f"Analise de intencao para '{chat_title}': {intent_data}")
    
    if intent_data["intent"] == "YES" and intent_data["keyword"]:
        from agente_navegador.actions.balao_search import search_balao_products
        
        keyword = intent_data["keyword"]
        products = await search_balao_products(keyword)
        
        if products:
            products.sort(key=lambda p: parse_price(p["price"]))
            
            _chat_sessions[chat_title] = {
                "keyword": keyword,
                "products": products,
                "current_index": 0,
                "last_direction": "forward"
            }
            
            await show_next_options(page, chat_title, require_confirmation)
        else:
            reply_text = await generate_friendly_no_products_response(user_message, keyword, history)
            await confirm_and_send_text(page, reply_text, require_confirmation, chat_title)
    else:
        reply_text = await generate_general_gemini_response(user_message, history)
        await confirm_and_send_text(page, reply_text, require_confirmation, chat_title)


async def run_auto_reply_loop(
    message_template: str,
    require_confirmation: bool = True,
    max_cycles: int = 5,
    cycle_delay_sec: int = 5
) -> int:
    """
    Executa o loop de verificacao e resposta automatica de vendas.
    Suporta selecao de contato via painel de controle global.
    """
    global _selected_chat_name
    page = await brw.get_page()
    replied_count = 0
    active_chat_title: str | None = None
    last_processed_msg_id: str | None = None
    
    log_agent(f"Iniciando loop de auto-resposta inteligente (Max ciclos: {max_cycles}, Delay: {cycle_delay_sec}s)")
    
    for cycle in range(max_cycles):
        # Se o operador selecionou um contato no painel, foca nele
        if _selected_chat_name:
            chat_name = _selected_chat_name
            log.info(f"Processando contato selecionado via painel: {chat_name}")
            _selected_chat_name = None
            await select_chat_by_name(chat_name)
            await asyncio.sleep(1.5)
            active_chat_title = chat_name
            last_processed_msg_id = None # Força a leitura/resposta no novo chat
            
        log.info(f"Ciclo {cycle + 1}/{max_cycles} - Verificando novas mensagens...")
        
        # 1. Encontra novos chats não lidos no menu lateral
        unread_chats = page.locator(f"xpath={UNREAD_CHAT_XPATH}")
        count = await unread_chats.count()
        
        new_chat_opened = False
        if count > 0:
            chat = unread_chats.first
            chat_title = "Contato Desconhecido"
            try:
                title_el = chat.locator("span[title], [data-testid='chat-title']")
                if await title_el.count() > 0:
                    chat_title = await title_el.first.get_attribute("title") or await title_el.first.inner_text() or chat_title
            except Exception as e:
                log.debug(f"Nao foi possivel ler o nome do contato: {e}")
                
            # Se for um contato diferente do ativo (ou se nenhum chat estiver aberto), foca nele
            if chat_title != active_chat_title or not active_chat_title:
                log_agent(f"Novo chat nao lido detectado de: '{chat_title}'. Abrindo...")
                await chat.click()
                await asyncio.sleep(1.5)
                active_chat_title = chat_title
                last_processed_msg_id = None
                new_chat_opened = True

        # 2. Se temos um chat ativo focado, monitoramos novas mensagens nele
        if active_chat_title:
            incoming_msgs = page.locator(LAST_INCOMING_MESSAGE)
            incoming_count = await incoming_msgs.count()
            
            if incoming_count > 0:
                last_msg = incoming_msgs.last
                
                # Obtém o data-id do Playwright como identificador único da mensagem
                msg_id = await get_message_id(last_msg)
                
                # Extrai o texto da mensagem do cliente
                last_msg_text = ""
                try:
                    text_el = last_msg.locator(MESSAGE_TEXT_SELECTOR)
                    if await text_el.count() > 0:
                        last_msg_text = await text_el.first.inner_text()
                except Exception as e:
                    log.debug(f"Nao foi possivel ler o texto da ultima mensagem: {e}")
                
                # Fallback para o texto se o data-id falhar
                if not msg_id:
                    msg_id = last_msg_text
                    
                # Se for uma mensagem nova do lead
                if msg_id != last_processed_msg_id:
                    log.info(f"Nova mensagem em '{active_chat_title}': '{last_msg_text}' (ID: {msg_id})")
                    
                    # Processa a resposta com contexto do histórico
                    if "supabase" in last_msg_text.lower():
                        await consult_supabase_source(page)
                        reply_text = "Ola! Abri a consulta interna da nossa base de dados Supabase para verificar as informacoes do seu cadastro/pedido. Um momento, por favor!"
                        await confirm_and_send_text(page, reply_text, require_confirmation, active_chat_title)
                        replied_count += 1
                    else:
                        history = await get_conversation_history(page)
                        await handle_whatsapp_message_flow(page, last_msg_text, history, require_confirmation, active_chat_title)
                        replied_count += 1
                    
                    # Atualiza o ID da última mensagem processada
                    last_processed_msg_id = msg_id
                else:
                    if not new_chat_opened:
                        log.info(f"Aguardando novas mensagens no chat ativo com '{active_chat_title}'...")
            else:
                log.info(f"Nenhuma mensagem recebida encontrada no chat de '{active_chat_title}'.")
        else:
            log.info("Nenhuma nova mensagem nos chats do menu lateral.")
            
        await asyncio.sleep(cycle_delay_sec)
        
    log_agent(f"Loop de auto-resposta inteligente concluido. Total respondido: {replied_count}")
    return replied_count
