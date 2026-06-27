"""
Modulo para raspagem e carregamento de dados institucionais do Balao da Informatica.
"""
from __future__ import annotations

import json
from pathlib import Path
from agente_navegador.logger import get_logger

log = get_logger(__name__)

# Caminho do cache local
CACHE_FILE = Path("data/company_info.json")

# Informacoes institucionais padrao (caso falhe a raspagem online)
DEFAULT_INFO = {
    "name": "Balao da Informatica Castelo",
    "address": "Av. Anchieta, 789 - Campinas/SP",
    "phone": "(19) 3255-1661",
    "whatsapp": "(19) 98751-0267",
    "email": "balaocastelo@gmail.com",
    "hours": "Segunda a Sexta das 08:00 as 18:00, Sábado das 08:00 as 13:00",
    "site": "www.balao.info",
    "description": "Loja de informática completa com PCs Gamer, notebooks, hardware, perifericos e assistencia tecnica especializada em Campinas e regiao."
}


def ensure_data_dir() -> None:
    """Garante que a pasta data/ existe."""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_company_info() -> dict[str, str]:
    """Retorna as informacoes institucionais da empresa salvas localmente."""
    ensure_data_dir()
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning(f"Erro ao ler cache de info da empresa: {e}")
            
    # Se nao existir ou der erro, salva as padrao
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_INFO, f, indent=4, ensure_ascii=False)
    except Exception as e:
        log.error(f"Erro ao salvar info da empresa padrao: {e}")
        
    return DEFAULT_INFO


async def scrape_company_info(page) -> dict[str, str]:
    """
    Acessa o site oficial e atualiza o perfil institucional da empresa.
    """
    log.info("Raspando informacoes institucionais de www.balao.info...")
    info = get_company_info().copy()
    
    try:
        new_page = await page.context.new_page()
        await new_page.goto("https://www.balao.info", wait_until="domcontentloaded")
        await new_page.wait_for_timeout(3000)
        
        # Tenta raspar dados estruturados de Schema.org ou tags HTML comuns
        scraped_data = await new_page.evaluate("""
            () => {
                const data = {};
                
                // Tenta ler do script ld+json
                const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                for (const script of scripts) {
                    try {
                        const json = JSON.parse(script.innerText);
                        const graph = json['@graph'] || [json];
                        for (const item of graph) {
                            if (item['@type'] && (item['@type'].includes('Store') || item['@type'].includes('LocalBusiness'))) {
                                if (item.telephone) data.phone = item.telephone;
                                if (item.email) data.email = item.email;
                                if (item.address && item.address.streetAddress) {
                                    data.address = `${item.address.streetAddress} - ${item.address.addressLocality}/${item.address.addressRegion}`;
                                }
                                break;
                            }
                        }
                    } catch(e) {}
                }
                
                // Fallback para elementos de texto comuns
                const bodyText = document.body.innerText || '';
                
                // Telefone/Whatsapp
                const phoneMatch = bodyText.match(/(?:\\(19\\)|19)\\s*9?[\\d-]{4,5}-[\\d-]{4}/g);
                if (phoneMatch && phoneMatch.length > 0) {
                    data.whatsapp = phoneMatch[0];
                }
                
                return data;
            }
        """)
        await new_page.close()
        
        # Atualiza apenas o que foi encontrado com sucesso
        if scraped_data:
            if "phone" in scraped_data:
                info["phone"] = scraped_data["phone"]
            if "email" in scraped_data:
                info["email"] = scraped_data["email"]
            if "address" in scraped_data:
                info["address"] = scraped_data["address"]
            if "whatsapp" in scraped_data:
                info["whatsapp"] = scraped_data["whatsapp"]
                
            # Salva no cache
            ensure_data_dir()
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(info, f, indent=4, ensure_ascii=False)
                
            log.info("Informacoes institucionais atualizadas com sucesso!")
        
    except Exception as e:
        log.error(f"Erro ao raspar dados de www.balao.info: {e}")
        
    return info
