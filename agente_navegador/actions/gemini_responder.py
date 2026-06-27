"""
Modulo de integracao com o Gemini para respostas inteligentes e personalizadas.
"""
from __future__ import annotations

from datetime import datetime
import google.generativeai as genai
from agente_navegador.config import config
from agente_navegador.logger import get_logger
from agente_navegador.actions.balao_search import search_balao_products

log = get_logger(__name__)


def get_time_greeting() -> str:
    """Retorna bom dia, boa tarde ou boa noite de acordo com a hora local do sistema."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "bom dia"
    elif 12 <= hour < 18:
        return "boa tarde"
    else:
        return "boa noite"

# Configura a API se a chave estiver presente
if config.gemini_api_key:
    genai.configure(api_key=config.gemini_api_key)
else:
    log.warning("GEMINI_API_KEY nao configurada no .env. O agente usara respostas estaticas.")

SYSTEM_INSTRUCTION = """
Você é o assistente virtual da empresa Balão da Informática Castelo (Campinas/SP).
Responda sempre de forma muito cordial, empática, demonstrando interesse real no assunto do cliente e prestativa em português.

Informações sobre a empresa:
- Nome: Balão da Informática Castelo
- Endereço: Av. Anchieta, 789 – Campinas/SP
- WhatsApp de Atendimento: (19) 98751-0267
- Telefone fixo: (19) 3255-1661
- Instagram: @balaodainformatica_castelo
- Site oficial: www.balao.info

Diretrizes de conversação:
1. Seja cordial, breve e conduza o atendimento mostrando entusiasmo e interesse real nas necessidades do lead.
2. Converse ativamente para entender os detalhes do que o cliente procura (ex: se ele quer um notebook para jogos, trabalho, quanta memória prefere, se quer com SSD, etc.) de modo a obter as melhores palavras-chave para pesquisa.
3. Nunca invente links de produtos. Use apenas os links fornecidos explicitamente no contexto.
4. Incentive o lead a visitar nosso site oficial www.balao.info para conferir os detalhes e comprar.
5. Se o cliente perguntar por produtos, utilize estritamente a lista de produtos sugerida no contexto.
6. NUNCA use a sintaxe de link do Markdown como `[texto](url)` ou parenteses em volta de links. Sempre escreva a URL pura diretamente, exatamente como fornecida (ex: Compre aqui: http://www.balao.info/...). Nunca envie a mesma URL duas vezes na mesma mensagem.
"""


async def generate_smart_response(user_message: str, history: list[dict] | None = None) -> str:
    """
    Gera uma resposta inteligente usando o Gemini baseada na intencao do lead,
    historico da conversa e integracao com busca do balao.info.
    """
    # Fallback estatico se nao houver chave API
    if not config.gemini_api_key:
        return _get_static_fallback(user_message)

    try:
        # Usamos gemini-2.5-flash para respostas rapidas e eficientes
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_INSTRUCTION
        )

        # Formata o histórico recente
        history_context = ""
        if history:
            history_context = "Histórico recente da conversa:\n"
            for msg in history:
                history_context += f"{msg['sender']}: {msg['text']}\n"
            history_context += "\n"

        # 1. Detectar intencao de busca de produto
        intent_prompt = (
            "Com base no histórico da conversa e na última mensagem do cliente, responda apenas 'YES' se ele "
            "estiver demonstrando interesse, perguntando ou tirando dúvidas sobre produtos de informática, peças, hardware, "
            "computadores, notebooks ou periféricos. Responda 'NO' caso contrário.\n\n"
            f"{history_context}"
            f"Última mensagem do Cliente: {user_message}"
        )
        intent_res = await model.generate_content_async(intent_prompt)
        intent = intent_res.text.strip().upper()
        
        products = []
        if "YES" in intent:
            # 2. Extrair palavra-chave para busca
            kw_prompt = (
                "Com base no histórico da conversa e na última mensagem, extraia a principal palavra-chave do produto "
                "que o cliente quer pesquisar no site (se ele especificou melhor ou mudou de item, extraia a nova palavra-chave). "
                "Responda APENAS com a palavra-chave (ex: 'notebook', 'ssd', 'placa de video').\n\n"
                f"{history_context}"
                f"Última mensagem do Cliente: {user_message}"
            )
            kw_res = await model.generate_content_async(kw_prompt)
            keyword = kw_res.text.strip().replace("'", "").replace('"', "")
            
            # Executa a busca real no site www.balao.info
            products = await search_balao_products(keyword)

        # 3. Gerar a resposta final contextualizada
        greeting = get_time_greeting()
        has_agent_replied = False
        if history:
            has_agent_replied = any(msg["sender"] == "Agente" for msg in history)
            
        if has_agent_replied:
            prompt = (
                f"Você é o Agente do Balão da Informática. A conversa já está em andamento (já houve saudações iniciais). "
                f"NUNCA use cumprimentos como 'bom dia', 'boa tarde', 'boa noite' ou 'olá' nesta resposta. "
                f"Responda à última mensagem do Cliente de forma direta, natural, simpática e muito curta/objetiva, sem repetir saudações.\n\n"
                f"{history_context}"
                f"Última mensagem do Cliente: '{user_message}'\n\n"
            )
        else:
            prompt = (
                f"Você é o Agente do Balão da Informática. Esta é a primeira resposta da conversa. "
                f"Use o cumprimento apropriado '{greeting}' ou 'olá' de forma natural no início se adequado. "
                f"Responda à última mensagem do Cliente de forma simpática, muito cordial, prestativa e mantendo o texto curto.\n\n"
                f"{history_context}"
                f"Última mensagem do Cliente: '{user_message}'\n\n"
            )
        if products:
            prompt += "Produtos reais e links correspondentes encontrados no nosso site www.balao.info:\n"
            for p in products:
                prompt += f"- {p['title']} por {p['price']} | Link: {p['link']}\n"
            prompt += "\nPor favor, sugira as opções acima de forma amigável e coloque os links para ele clicar."
        else:
            if "YES" in intent:
                prompt += (
                    "Nota: Não encontramos produtos correspondentes específicos na busca imediata do site. "
                    "Responda educadamente dizendo que podemos cotar ou encomendar e indique nosso site www.balao.info."
                )

        final_res = await model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
        return final_res.text.strip()

    except Exception as e:
        log.error(f"Erro ao gerar resposta com Gemini: {e}")
        return _get_static_fallback(user_message, history)


def _get_static_fallback(user_message: str, history: list[dict] | None = None) -> str:
    """Gera uma resposta estatica amigavel se a IA falhar ou nao estiver configurada."""
    msg_lower = user_message.lower()
    
    # Verifica se o agente já respondeu no histórico para evitar saudações repetidas
    has_agent_replied = any(msg["sender"] == "Agente" for msg in history) if history else False
    greet_prefix = "" if has_agent_replied else f"{get_time_greeting().capitalize()}! "
    
    if "endereco" in msg_lower or "onde fica" in msg_lower or "localizacao" in msg_lower:
        return (
            f"{greet_prefix}Fica no Cambui: Av. Anchieta, 789 – Campinas/SP. "
            "Nosso site e www.balao.info. Como posso te ajudar hoje?"
        )
    if "contato" in msg_lower or "telefone" in msg_lower or "whatsapp" in msg_lower:
        return (
            f"{greet_prefix}Voce pode nos contatar no telefone (19) 3255-1661 ou WhatsApp (19) 98751-0267. "
            "Acesse tambem nosso site www.balao.info!"
        )
        
    return (
        f"{greet_prefix}Agradecemos seu contato com o Balao da Informatica Castelo. "
        "Recebemos sua mensagem e em breve um de nossos especialistas ira te responder!"
    )


async def classify_follow_up_intent(user_message: str, history: list[dict] | None = None) -> str:
    """
    Classifica se a resposta do cliente indica interesse em ver produtos 'CHEAPER' (mais baratos),
    'EXPENSIVE' (mais caras/mais itens), 'NEW_SEARCH' (se ele mudou de assunto/produto)
    ou 'OTHER' (outras conversas).
    """
    if not config.gemini_api_key:
        msg_lower = user_message.lower()
        if any(w in msg_lower for w in ["barat", "baixo", "menor", "desconto"]):
            return "CHEAPER"
        if any(w in msg_lower for w in ["car", "alt", "maior", "melhor", "mais"]):
            return "EXPENSIVE"
        return "OTHER"

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction="Você é um classificador de intenções de conversação de e-commerce."
        )
        
        history_context = ""
        if history:
            history_context = "Histórico da Conversa:\n"
            for msg in history:
                history_context += f"{msg['sender']}: {msg['text']}\n"
            history_context += "\n"

        prompt = (
            "Analise a última mensagem do cliente e classifique em uma das seguintes opções:\n"
            "1. 'CHEAPER': Se o cliente deseja ver opções de produtos mais baratos, menor preço ou com desconto em relação aos mostrados anteriormente.\n"
            "2. 'EXPENSIVE': Se o cliente deseja ver opções de produtos mais caros, de melhor desempenho, de maior valor ou simplesmente ver mais opções/outros modelos.\n"
            "3. 'NEW_SEARCH': Se o cliente mudou totalmente de assunto e quer pesquisar um produto diferente (ex: ele estava falando de notebooks e agora pediu teclado).\n"
            "4. 'OTHER': Se for uma resposta geral (ex: 'obrigado', 'vou ver', 'ok', tirar outra dúvida, etc.).\n\n"
            "Responda APENAS com uma das quatro palavras: CHEAPER, EXPENSIVE, NEW_SEARCH ou OTHER.\n\n"
            f"{history_context}"
            f"Última mensagem do Cliente: '{user_message}'"
        )
        
        res = await model.generate_content_async(prompt)
        decision = res.text.strip().upper()
        
        if "CHEAPER" in decision:
            return "CHEAPER"
        elif "EXPENSIVE" in decision:
            return "EXPENSIVE"
        elif "NEW_SEARCH" in decision:
            return "NEW_SEARCH"
        else:
            return "OTHER"
    except Exception as e:
        log.error(f"Erro ao classificar follow up: {e}")
        return "OTHER"


async def analyze_message_intent_and_keyword(user_message: str, history: list[dict] | None = None) -> dict:
    """
    Analisa se a mensagem indica intenção de busca de produto ('YES' ou 'NO')
    e extrai a palavra-chave.
    """
    if not config.gemini_api_key:
        return {"intent": "NO", "keyword": ""}

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash"
        )
        
        history_context = ""
        if history:
            history_context = "Histórico da Conversa:\n"
            for msg in history:
                history_context += f"{msg['sender']}: {msg['text']}\n"
            history_context += "\n"

        intent_prompt = (
            "Com base no histórico da conversa e na última mensagem do cliente, responda apenas 'YES' se ele "
            "estiver demonstrando interesse, perguntando ou tirando dúvidas sobre produtos de informática, peças, hardware, "
            "computadores, notebooks ou periféricos. Responda 'NO' caso contrário.\n\n"
            f"{history_context}"
            f"Última mensagem do Cliente: {user_message}"
        )
        intent_res = await model.generate_content_async(intent_prompt)
        intent = intent_res.text.strip().upper()
        
        keyword = ""
        if "YES" in intent:
            kw_prompt = (
                "Com base no histórico da conversa e na última mensagem, extraia as principais palavras-chave do produto "
                "que o cliente quer pesquisar no site, combinando o tipo do produto com as especificações solicitadas "
                "(ex: marca, capacidade de memória RAM, armazenamento SSD/HD, processador, cor, etc.) "
                "de forma a gerar a melhor busca possível. "
                "Responda APENAS com a busca simplificada contendo as palavras-chave separadas por espaço (ex: 'notebook 16gb ssd 512', 'placa de video rtx', 'ssd 240gb'). "
                "Não use vírgulas ou pontuações.\n\n"
                f"{history_context}"
                f"Última mensagem do Cliente: {user_message}"
            )
            kw_res = await model.generate_content_async(kw_prompt)
            keyword = kw_res.text.strip().replace("'", "").replace('"', "")
            
        return {"intent": "YES" if "YES" in intent else "NO", "keyword": keyword}
    except Exception as e:
        log.error(f"Erro ao analisar intenção: {e}")
        return {"intent": "NO", "keyword": ""}


async def generate_friendly_no_products_response(user_message: str, keyword: str, history: list[dict] | None = None) -> str:
    """Gera uma resposta amigavel quando nao ha produtos em estoque."""
    if not config.gemini_api_key:
        return _get_static_fallback(user_message, history)
        
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_INSTRUCTION
        )
        history_context = ""
        if history:
            history_context = "Histórico recente da conversa:\n"
            for msg in history:
                history_context += f"{msg['sender']}: {msg['text']}\n"
            history_context += "\n"
            
        greeting = get_time_greeting()
        has_agent_replied = any(msg["sender"] == "Agente" for msg in history) if history else False
        
        if has_agent_replied:
            prompt = (
                f"Responda ao cliente explicando educadamente que no momento não encontramos opções de '{keyword}' em estoque no site. "
                "Recomende dar uma olhada no site completo www.balao.info ou pergunte se deseja cotação. "
                "A conversa já está em andamento, então NUNCA use cumprimentos (como olá, bom dia/tarde/noite). Vá direto ao ponto de forma curta e natural.\n\n"
                f"{history_context}"
                f"Última mensagem: {user_message}"
            )
        else:
            prompt = (
                f"Responda ao cliente explicando educadamente que no momento não encontramos opções de '{keyword}' em estoque no site. "
                "Recomende dar uma olhada no site completo www.balao.info ou pergunte se deseja cotação. "
                f"Esta é a primeira mensagem, então use o cumprimento '{greeting}' de forma natural no início.\n\n"
                f"{history_context}"
                f"Última mensagem: {user_message}"
            )
        res = await model.generate_content_async(prompt)
        return res.text.strip()
    except Exception:
        return _get_static_fallback(user_message, history)


async def generate_general_gemini_response(user_message: str, history: list[dict] | None = None) -> str:
    """Gera uma resposta geral usando o Gemini para tirar duvidas gerais."""
    if not config.gemini_api_key:
        return _get_static_fallback(user_message, history)
        
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_INSTRUCTION
        )
        history_context = ""
        if history:
            history_context = "Histórico recente da conversa:\n"
            for msg in history:
                history_context += f"{msg['sender']}: {msg['text']}\n"
            history_context += "\n"
            
        greeting = get_time_greeting()
        has_agent_replied = any(msg["sender"] == "Agente" for msg in history) if history else False
        
        if has_agent_replied:
            prompt = (
                "Responda à última mensagem do cliente de forma amigável, muito curta e direta, sem repetir saudações ou cumprimentos (como olá, bom dia/noite), pois a conversa já está em andamento.\n\n"
                f"{history_context}"
                f"Última mensagem: {user_message}"
            )
        else:
            prompt = (
                f"Responda à última mensagem do cliente de forma amigável, cordial e curta. Use a saudação '{greeting}' no início de forma natural.\n\n"
                f"{history_context}"
                f"Última mensagem: {user_message}"
            )
        res = await model.generate_content_async(prompt)
        return res.text.strip()
    except Exception:
        return _get_static_fallback(user_message, history)


async def generate_clarifying_question(user_message: str, history: list[dict] | None = None, keyword: str = "") -> str:
    """Gera uma pergunta cordial e especifica para qualificar o lead antes da busca."""
    if not config.gemini_api_key:
        return _get_static_fallback(user_message, history)
        
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_INSTRUCTION
        )
        history_context = ""
        if history:
            history_context = "Histórico recente da conversa:\n"
            for msg in history:
                history_context += f"{msg['sender']}: {msg['text']}\n"
            history_context += "\n"
            
        greeting = get_time_greeting()
        has_agent_replied = any(msg["sender"] == "Agente" for msg in history) if history else False
        
        if has_agent_replied:
            prompt = (
                f"O cliente está interessado em '{keyword}'. Faça uma nova pergunta muito cordial para entender melhor a necessidade "
                f"(ex: preferência de marca, capacidade, uso, ou orçamento) para podermos fazer a melhor busca no site depois. "
                f"ATENÇÃO: NUNCA use cumprimentos (como olá, bom dia/noite) pois a conversa já está em andamento. "
                f"Seja breve, empático, muito curto e faça apenas uma pergunta de esclarecimento por vez.\n\n"
                f"{history_context}"
                f"Última mensagem: {user_message}"
            )
        else:
            prompt = (
                f"O cliente está interessado em '{keyword}'. Mostre entusiasmo e interesse real. "
                f"Use a saudação inicial '{greeting}' de forma natural e faça uma primeira pergunta para entender a necessidade (ex: objetivo de uso do item).\n\n"
                f"{history_context}"
                f"Última mensagem: {user_message}"
            )
            
        res = await model.generate_content_async(prompt)
        return res.text.strip()
    except Exception:
        return _get_static_fallback(user_message, history)
