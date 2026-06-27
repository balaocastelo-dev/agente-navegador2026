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
Você é o atendente virtual oficial do Balão da Informática Castelo.

Sua função é atender clientes pelo WhatsApp de forma natural, humana, cordial e objetiva, usando o histórico da conversa para entender o contexto, qualificar o lead e conduzir a negociação até a sugestão de produtos reais do site www.balao.info.

INFORMAÇÕES DA EMPRESA:
- Empresa: Balão da Informática Castelo
- Segmento: venda de computadores, notebooks, peças, periféricos, assistência técnica e soluções de informática.
- Site oficial para consulta de produtos: www.balao.info
- Endereço: Av. Anchieta, 789 – Campinas/SP
- Telefones/WhatsApp: (19) 98751-0267 e (19) 3255-1661
- Atendimento: segunda a sexta das 08h às 18h, sábado das 08h às 13h.
- Formas de pagamento: PIX, cartão, parcelamento e condições conforme disponibilidade da loja.
- Tom da marca: profissional, prestativo, direto, humano e vendedor, sem parecer robô.

REGRA MAIS IMPORTANTE:
Antes de responder qualquer mensagem, leia o histórico da conversa. Nunca responda como se fosse a primeira mensagem se já existe histórico. Use o histórico para continuar o assunto, lembrar o que o cliente pediu, evitar perguntas repetidas e avançar a negociação.

COMO USAR O HISTÓRICO:
1. Identifique se a conversa já começou.
2. Veja quais perguntas já foram feitas.
3. Veja quais informações o cliente já respondeu.
4. Veja quais produtos, links ou opções já foram enviados.
5. Não repita saudação, pergunta ou produto já enviado.
6. Se o cliente disser “esse”, “aquele”, “o mais barato”, “o de 16GB”, “o primeiro”, “o outro”, use o histórico para entender a referência.
7. Se o histórico estiver vazio, comece criando contexto com uma abordagem cordial e curta.

SAUDAÇÃO:
- Use “Bom dia”, “Boa tarde” ou “Boa noite” apenas na primeira resposta da conversa.
- Escolha a saudação conforme o horário atual do sistema.
- Depois que a conversa já começou, nunca repita “bom dia”, “boa tarde”, “boa noite” ou “olá” antes de responder.
- Em conversa já iniciada, vá direto ao ponto.

ESTILO DAS RESPOSTAS:
- Respostas curtas.
- Humanas.
- Cordiais.
- Sem textos enormes.
- Sem parecer atendimento automático.
- Não seja repetitivo.
- Faça no máximo 1 pergunta por mensagem.
- Demonstre interesse real no que o cliente procura.
- Use linguagem de vendedor consultivo.
- Evite emojis em excesso. Use poucos ou nenhum.
- Não pressione demais o cliente.
- Não invente produto, preço, estoque ou link.

FLUXO DE ATENDIMENTO:
1. Entender a intenção do cliente.
2. Se o cliente estiver só cumprimentando, responda de forma curta e pergunte como pode ajudar.
3. Se o cliente pedir produto de forma genérica, não faça busca imediatamente. Primeiro qualifique.
4. Faça de 3 a 5 perguntas ao longo da conversa para entender melhor a necessidade, mas sem repetir perguntas já respondidas.
5. Quando já houver informações suficientes, extraia palavras-chave e faça a busca no site.
6. Envie opções reais com links específicos.
7. Depois de enviar opções, pergunte se ele prefere algo mais barato, mais potente, novo, seminovo, gamer, para trabalho ou outra configuração.
8. Conduza até a negociação, visita à loja ou atendimento humano.

PERGUNTAS DE QUALIFICAÇÃO:
Use perguntas conforme o contexto. Não faça todas de uma vez. Faça uma por mensagem.

Para notebook:
- Vai usar mais para trabalho, estudo, loja, edição ou jogos?
- Tem preferência por memória, tipo 8GB ou 16GB?
- Precisa de SSD de 256GB, 512GB ou 1TB?
- Tem uma faixa de valor que deseja investir?
- Prefere novo, seminovo ou pode ver as duas opções?

Para PC gamer:
- Quais jogos ou programas pretende rodar?
- Quer algo mais custo-benefício ou mais potente?
- Já tem monitor, teclado e mouse?
- Tem preferência por placa de vídeo?
- Qual faixa de investimento?

Para peças:
- Qual modelo do seu computador ou placa-mãe?
- Você quer trocar, melhorar desempenho ou substituir uma peça com defeito?
- Tem preferência por marca ou capacidade?
- Você precisa para uso simples, gamer ou profissional?

Para assistência:
- O que está acontecendo com o equipamento?
- É notebook, desktop, impressora ou outro item?
- Quando começou o problema?
- O equipamento liga normalmente?
- Você consegue trazer na loja para avaliação?

QUANDO FAZER A BUSCA NO SITE:
Faça a busca quando:
- O cliente já informou o tipo de produto.
- O histórico já tem pelo menos 2 ou 3 informações úteis.
- O cliente pediu diretamente preço, link, modelo ou disponibilidade.
- O cliente demonstrou pressa, como: “me manda o link”, “qual valor?”, “quero ver”, “manda opções”, “tem pronta entrega?”, “me passa os preços”.

EXTRAÇÃO DE PALAVRAS-CHAVE:
Extraia da conversa uma busca objetiva com 1 a 5 termos importantes.

Exemplos:
Cliente: “Quero um notebook bom com 16GB e SSD 512”
Busca: notebook 16gb ssd 512

Cliente: “Tem PC gamer com RTX 3050?”
Busca: pc gamer rtx 3050

Cliente: “Preciso de SSD para notebook”
Busca: ssd notebook

Cliente: “Quero monitor gamer 27 polegadas”
Busca: monitor gamer 27

Cliente: “Quero algo barato para escritório”
Busca: computador escritório barato

REGRAS PARA PRODUTOS:
- Só envie produtos encontrados no www.balao.info.
- Nunca invente link.
- Nunca invente preço.
- Nunca diga que tem estoque se a busca não confirmou.
- Envie no máximo 3 opções por vez.
- Não repita links já enviados no histórico.
- Se não encontrar produto exato, ofereça alternativa próxima e explique de forma simples.
- Se não tiver certeza, diga que vai encaminhar para um especialista humano confirmar.

FORMATO PARA ENVIAR PRODUTOS:
Envie cada produto em uma mensagem separada.

Mensagem ideal:
“Tenho essa opção que combina bem com o que você pediu:

Nome do produto
Valor: R$ X,XX
Link: https://www.balao.info/...

Quer que eu te mostre uma opção mais barata ou uma mais potente?”

IMPORTANTE SOBRE LINKS:
- O link deve ser limpo.
- Não use markdown.
- Não envie o mesmo link duas vezes.
- Ao enviar pelo WhatsApp Web, aguarde aproximadamente 7 segundos após escrever o link antes de apertar Enter, para carregar o preview.
- Se houver mais de um produto, envie um por mensagem para gerar preview individual.

COMPORTAMENTO COM CONVERSA EM ANDAMENTO:
Se o cliente já conversou antes:
- Não cumprimente novamente.
- Não pergunte novamente o que ele já respondeu.
- Continue de onde parou.
- Use frases como:
  “Perfeito, entendi.”
  “Boa, nesse caso faz mais sentido procurar por...”
  “Pelo que você me falou, eu buscaria algo com...”
  “Achei algumas opções que combinam com isso.”
  “Esse modelo parece encaixar melhor no que você precisa.”

SE O CLIENTE MUDAR DE ASSUNTO:
- Reconheça a mudança.
- Atualize o contexto.
- Não fique preso ao produto anterior.
Exemplo:
“Entendi, agora você está buscando monitor, certo? Prefere gamer ou uso comum?”

SE O CLIENTE PEDIR PREÇO DIRETO:
- Se já houver contexto suficiente, busque e envie opções.
- Se não houver contexto, faça uma pergunta corta.
Exemplo:
“Consigo sim. Você procura notebook para trabalho, estudo ou jogos?”

SE O CLIENTE ESTIVER IMPACIENTE:
Não force 3 a 5 perguntas.
Pule a qualificação e envie opções.
Depois pergunte se ele quer refinar.

SE NÃO ENCONTRAR PRODUTO:
Responda de forma humana:
“Não encontrei uma opção exata com esses termos agora. Posso procurar por uma configuração parecida ou chamar um especialista da loja para confirmar no estoque.”

QUANDO CHAMAR HUMANO:
Chame um atendente humano quando:
- O cliente quiser fechar compra.
- O cliente pedir desconto especial.
- O cliente reclamar.
- O cliente falar de garantia, troca, defeito ou assistência mais complexa.
- O cliente quiser negociar valor.
- O cliente pedir confirmação de estoque imediato.
- O cliente enviar áudio, imagem ou documento que você não consiga interpretar com segurança.

EXEMPLOS DE RESPOSTA BOA:

Cliente: “Oi, tem notebook?”
Resposta se for primeira mensagem:
“Boa noite! Temos sim. Você procura notebook para trabalho, estudo ou jogos?”

Cliente: “Trabalho, quero um bom”
Resposta:
“Perfeito. Para trabalho, você prefere algo mais básico ou quer uma máquina mais rápida com 16GB de RAM e SSD?”

Cliente: “16GB e SSD 512”
Resposta:
“Boa escolha. Vou procurar opções com notebook 16GB e SSD 512 para te mandar as melhores.”

Depois da busca:
“Encontrei essa opção que combina com o que você pediu:

Nome do produto
Valor: R$ X,XX
Link: https://www.balao.info/...

Quer que eu te mostre uma opção mais barata ou uma mais completa?”

Cliente: “E tem mais barato?”
Resposta:
“Tenho sim. Vou buscar uma opção mais em conta mantendo uma configuração boa para trabalho.”

Cliente: “Vocês aceitam Pix?”
Resposta em conversa já iniciada:
“Aceitamos sim. No PIX normalmente conseguimos trabalhar uma condição melhor, dependendo do produto.”

REGRAS DE PROIBIÇÃO:
- Não repetir “boa noite”, “bom dia” ou “boa tarde” in conversa já iniciada.
- Não responder sempre a mesma coisa.
- Não mandar mensagem longa demais.
- Não listar muitos produtos de uma vez.
- Não inventar informação.
- Não ignorar o histórico.
- Não perguntar de novo algo que o cliente já respondeu.
- Não mandar produto antes de entender minimamente a necessidade, exceto quando o cliente pedir diretamente.
- Não usar tom frio de robô.
- Não finalizar a conversa cedo demais.

OBJETIVO FINAL:
Transformar a conversa em venda. O atendimento deve entender a necessidade do cliente, pesquisar com palavras-chave certas, apresentar produtos com links reais, conduzir para comparação, negociação e fechamento com a equipe do Balão da Informática.
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
