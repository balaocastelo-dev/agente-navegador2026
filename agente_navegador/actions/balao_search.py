"""
Busca de produtos no site oficial www.balao.info.
"""
from __future__ import annotations

from typing import Dict, List
import httpx
from bs4 import BeautifulSoup

from agente_navegador.logger import get_logger

log = get_logger(__name__)

BASE_URL = "https://www.balao.info"


async def search_balao_products(query: str) -> List[Dict[str, str]]:
    """
    Pesquisa produtos no site www.balao.info para o termo fornecido.
    Retorna uma lista de dicionarios contendo title, price e link.
    """
    if not query or len(query.strip()) < 2:
        return []

    search_url = f"{BASE_URL}/?search={query.strip()}"
    log.info(f"Buscando produtos no balao.info para '{query}'...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(search_url, headers=headers)
            
            if response.status_code != 200:
                log.warning(f"Erro ao buscar no balao.info. Status code: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            
            # Encontra todos os cards de produto
            # Seletor baseado em div.grid > div.group ou qualquer div contendo links de produto
            products = []
            
            # Procuramos os cards de produtos baseados em links ou estrutura de h3
            cards = soup.select("div.group") or soup.find_all("div", class_="group")
            
            if not cards:
                # Fallback: tentar encontrar h3 com links proximos
                cards = soup.select("div.grid > div")
                
            for card in cards:
                try:
                    title_el = card.find("h3")
                    price_el = card.select_one("span.font-extrabold") or card.find(class_="font-extrabold")
                    link_el = card.find("a", href=True)
                    
                    if title_el and link_el:
                        title = title_el.get_text(strip=True)
                        price = price_el.get_text(strip=True) if price_el else "Preco sob consulta"
                        href = link_el["href"]
                        
                        # Completa o link relativo
                        link = href if href.startswith("http") else f"{BASE_URL}{href}"
                        
                        # Filtro basico para garantir que e um link de produto
                        if "/product/" in link or "search=" not in href:
                            products.append({
                                "title": title,
                                "price": price,
                                "link": link
                            })
                except Exception as card_err:
                    log.debug(f"Erro ao processar card de produto no scraping: {card_err}")
                    continue

            log.info(f"Busca finalizada. Encontrados {len(products)} produtos para '{query}'.")
            return products[:5]  # Retorna no maximo 5 produtos relevantes

    except Exception as e:
        log.error(f"Erro durante a requisicao de busca ao balao.info: {e}")
        return []
