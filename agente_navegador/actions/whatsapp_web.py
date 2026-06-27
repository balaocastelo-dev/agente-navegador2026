"""
Acoes especificas para WhatsApp Web (autenticacao por QR Code).

Este modulo fornece helpers para monitorar novas mensagens e enviar respostas
automoticas de forma supervisionada, integrando buscas no site oficial
www.balao.info e consulta direta no Supabase.
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


def extract_search_term(message: str) -> str | None:
    """
    Detecta se o usuario esta perguntando por produtos e extrai o termo de busca.
    """
    msg = message.lower().strip()
    
    # Palavras-chave que indicam interesse em comprar/saber preco
    intent_keywords = [
        "preço", "preco", "quanto custa", "valor", "tem", "têm", "disponível", "disponivel",
        "comprar", "gostaria de saber", "qual o preço", "qual o preco", "quanto tá", "quanto ta"
    ]
    
    is_product_query = any(kw in msg for kw in intent_keywords)
    
    # Lista de termos de produtos comuns para verificar
    product_keywords = [
        "computador", "pc", "gamer", "notebook", "apple", "iphone", "ipad", "macbook",
        "teclado", "mouse", "monitor", "headset", "fone", "cadeira", "ssd", "hd", "placa",
        "memoria", "ram", "cooler", "fonte", "gabinete", "processador"
    ]
    
    has_product = any(prod in msg for prod in product_keywords)
    
    if not (is_product_query or has_product):
        return None

    # Limpa a mensagem para tentar pegar apenas o nome do produto
    cleaned = msg
    for phrase in intent_keywords:
        cleaned = cleaned.replace(phrase, "")
    for word in ["olá", "ola", "bom dia", "boa tarde", "boa noite", "por favor", "vocês", "voces"]:
        cleaned = cleaned.replace(word, "")
        
    cleaned = cleaned.strip("? .! \n\t,;*")
    
    # Se sobrar alguma coisa, usamos como termo de busca. Caso contrario, usamos um padrao.
    if len(cleaned) >= 2:
        return cleaned
    
    # Fallback inteligente baseado em palavra encontrada
    for prod in product_keywords:
        if prod in msg:
            return prod
            
    return "computador"


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
        
        # Extrai links de produtos que possuem /product/ e contem R$
        products = await new_page.evaluate("""
            () => {
                const results = [];
                const anchors = document.querySelectorAll('a');
                for (const a of anchors) {
                    if (a.href && a.href.includes('/product/')) {
                        const text = a.innerText.trim();
                        if (text.includes('R$')) {
                            const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                            
                            // Ignora a categoria se estiver na primeira linha em maiusculas
                            let name = lines[0];
                            if (lines.length > 1 && lines[0] === lines[0].toUpperCase() && lines[0].length < 25) {
                                name = lines[1];
                            }
                            
                            // Pega o preco real
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
        return products[:3] # Retorna as 3 melhores ofertas
    except Exception as e:
        log.error(f"Erro ao pesquisar produtos no balao.info: {e}")
        return []


async def consult_supabase_source(page) -> None:
    """
    Abre o Supabase em uma nova aba para consulta.
    Usa o perfil persistente para carregar a sessao existente do usuario.
    """
    log_agent("Navegando para o Supabase (fonte de dados)...")
    try:
        new_page = await page.context.new_page()
        await new_page.goto("https://ptqqvezawobgnheesgvh.supabase.co")
        log_success("Aba do Supabase aberta com sucesso. Se necessario, realize o login.")
        # Deixa a aba aberta por 10 segundos para carregar e depois mantem ela no contexto
        await new_page.wait_for_timeout(10000)
    except Exception as e:
        log.error(f"Erro ao abrir Supabase: {e}")


async def run_auto_reply_loop(
    message_template: str,
    require_confirmation: bool = True,
    max_cycles: int = 5,
    cycle_delay_sec: int = 5
) -> int:
    """
    Executa o loop de verificacao e resposta automatica.
    Identifica se a mensagem eh de vendas, busca no site balao.info, e responde.
    """
    page = await brw.get_page()
    replied_count = 0
    
    log_agent(f"Iniciando loop de auto-resposta de vendas (Max ciclos: {max_cycles}, Delay: {cycle_delay_sec}s)")
    
    for cycle in range(max_cycles):
        log.info(f"Ciclo {cycle + 1}/{max_cycles} - Verificando novas mensagens...")
        
        # Encontra chats nao lidos usando o XPath robusto
        unread_chats = page.locator(f"xpath={UNREAD_CHAT_XPATH}")
        count = await unread_chats.count()
        
        if count > 0:
            log.info(f"Encontrado(s) {count} chat(s) com mensagens nao lidas.")
            chat = unread_chats.first
            
            # Tenta obter o nome do contato/grupo
            chat_title = "Contato Desconhecido"
            try:
                title_el = chat.locator("span[title], [data-testid='chat-title']")
                if await title_el.count() > 0:
                    chat_title = await title_el.first.get_attribute("title") or await title_el.first.inner_text() or chat_title
            except Exception as e:
                log.debug(f"Nao foi possivel ler o nome do contato: {e}")
                
            log_agent(f"Abrindo chat de: '{chat_title}'")
            await chat.click()
            await asyncio.sleep(1.5)
            
            # Tenta capturar a ultima mensagem recebida para processar
            last_msg_text = ""
            try:
                incoming_msgs = page.locator(LAST_INCOMING_MESSAGE)
                if await incoming_msgs.count() > 0:
                    last_msg = incoming_msgs.last
                    text_el = last_msg.locator(MESSAGE_TEXT_SELECTOR)
                    if await text_el.count() > 0:
                        last_msg_text = await text_el.first.inner_text()
            except Exception as e:
                log.debug(f"Nao foi possivel ler a ultima mensagem: {e}")
                
            log.info(f"Mensagem recebida de '{chat_title}': '{last_msg_text}'")
            
            # Verifica se o cliente quer ver o Supabase (para o operador)
            if "supabase" in last_msg_text.lower():
                await consult_supabase_source(page)
                # Responde informando que abriu a consulta interna
                reply_text = "Ola! Abri a consulta interna da nossa base de dados Supabase para verificar as informacoes do seu cadastro/pedido. Um momento, por favor!"
            else:
                # Detecta se a mensagem contem uma consulta de produtos
                search_term = extract_search_term(last_msg_text)
                
                if search_term:
                    # Busca ofertas reais no site balao.info
                    products = await search_products_on_balao(page, search_term)
                    
                    if products:
                        reply_text = (
                            f"Ola! Sou o assistente virtual de vendas do Balão da Informática Castelo! 🚀\n\n"
                            f"Encontrei estas ofertas incriveis de *{search_term}* no nosso site:\n\n"
                        )
                        for p in products:
                            reply_text += f"📦 *{p['name']}*\n💰 Preço: {p['price']}\n🔗 Compra rápida: {p['link']}\n\n"
                        reply_text += "Qual dessas opcoes voce gostaria de garantir? Podemos entregar hoje mesmo! 🛍"
                    else:
                        reply_text = (
                            f"Ola! Sou o assistente virtual de vendas do Balão da Informática Castelo! 🚀\n\n"
                            f"Nao encontrei ofertas de *{search_term}* no site agora, mas temos muitos itens em estoque! "
                            f"Visite nosso site completo: www.balao.info ou me diga qual outra peca voce procura!"
                        )
                else:
                    # Se nao for consulta de produtos, envia o template de boas-vindas padrao
                    reply_text = message_template

            # Verifica se precisa de confirmacao do operador
            should_send = True
            if require_confirmation:
                should_send = confirm_critical_action(
                    f"Responder para '{chat_title}' com:\n\n{reply_text}"
                )
                
            if should_send:
                await page.wait_for_selector(INPUT_TEXTBOX, timeout=5000)
                input_field = page.locator(INPUT_TEXTBOX).first
                await input_field.click()
                await asyncio.sleep(0.5)
                
                # Simula digitacao humana com atrasos aleatorios entre os caracteres
                log.info(f"Digitando resposta para {chat_title}...")
                for char in reply_text:
                    await input_field.press(char)
                    await asyncio.sleep(random.uniform(0.02, 0.06))
                    
                await asyncio.sleep(0.5)
                await page.keyboard.press("Enter")
                log_success(f"Resposta enviada para '{chat_title}'!")
                replied_count += 1
            else:
                log.warning(f"Resposta para '{chat_title}' recusada pelo operador.")
                
            await asyncio.sleep(2)
        else:
            log.info("Nenhuma nova mensagem encontrada.")
            
        await asyncio.sleep(cycle_delay_sec)
        
    log_agent(f"Loop de auto-resposta concluido. Total respondido: {replied_count}")
    return replied_count
