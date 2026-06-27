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
Responda sempre de forma profissional, atenciosa e prestativa em português.

Informações sobre a empresa:
- Nome: Balão da Informática Castelo
- Endereço: Av. Anchieta, 789 – Campinas/SP
- WhatsApp de Atendimento: (19) 98751-0267
- Telefone fixo: (19) 3255-1661
- Instagram: @balaodainformatica_castelo
- Site oficial: www.balao.info

Diretrizes de conversação:
1. Seja cordial e breve nas mensagens.
2. Nunca invente links de produtos. Use apenas os links fornecidos explicitamente no contexto.
3. Incentive o lead a visitar nosso site oficial www.balao.info para conferir os detalhes e comprar.
4. Se o cliente perguntar por produtos, utilize estritamente a lista de produtos sugerida no contexto.
"""


async def generate_smart_response(user_message: str) -> str:
    """
    Gera uma resposta inteligente usando o Gemini baseada na intencao do lead
    e integracao com busca do balao.info.
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

        # 1. Detectar intencao de busca de produto
        intent_prompt = (
            "Responda apenas 'YES' se a mensagem a seguir for uma pergunta, dúvida ou solicitação sobre "
            "produtos de informática, peças, hardware, computadores, notebooks ou periféricos. "
            f"Responda 'NO' caso contrário.\nMensagem: {user_message}"
        )
        intent_res = await model.generate_content_async(intent_prompt)
        intent = intent_res.text.strip().upper()
        
        products = []
        if "YES" in intent:
            # 2. Extrair palavra-chave para busca
            kw_prompt = (
                "Extraia a principal palavra-chave do produto solicitado pelo cliente para pesquisarmos no site. "
                "Responda APENAS com a palavra-chave (ex: 'notebook', 'ssd', 'placa de video', 'mouse'). "
                f"Mensagem: {user_message}"
            )
            kw_res = await model.generate_content_async(kw_prompt)
            keyword = kw_res.text.strip().replace("'", "").replace('"', "")
            
            # Executa a busca real no site www.balao.info
            products = await search_balao_products(keyword)

        # 3. Gerar a resposta final contextualizada
        greeting = get_time_greeting()
        prompt = f"Cumprimento/Saudação a usar (conforme hora atual do sistema): '{greeting}'. Use-o de forma natural no início se adequado.\n"
        prompt += f"Mensagem do Lead: '{user_message}'\n\n"
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
        return _get_static_fallback(user_message)


def _get_static_fallback(user_message: str) -> str:
    """Gera uma resposta estatica amigavel se a IA falhar ou nao estiver configurada."""
    msg_lower = user_message.lower()
    greet = get_time_greeting().capitalize()
    
    if "endereco" in msg_lower or "onde fica" in msg_lower or "localizacao" in msg_lower:
        return (
            f"{greet}! Fica no Cambui: Av. Anchieta, 789 – Campinas/SP. "
            "Nosso site e www.balao.info. Como posso te ajudar hoje?"
        )
    if "contato" in msg_lower or "telefone" in msg_lower or "whatsapp" in msg_lower:
        return (
            f"{greet}! Voce pode nos contatar no telefone (19) 3255-1661 ou WhatsApp (19) 98751-0267. "
            "Acesse tambem nosso site www.balao.info!"
        )
        
    return (
        f"{greet}! Agradecemos seu contato com o Balao da Informatica Castelo. "
        "Recebemos sua mensagem e em breve um de nossos especialistas ira te responder!"
    )
