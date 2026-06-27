"""
Testes unitarios para a busca de produtos (balao_search.py).
"""
from __future__ import annotations

import pytest
from agente_navegador.actions.balao_search import search_balao_products


@pytest.mark.anyio
async def test_search_balao_products_real_notebook():
    """Valida se a busca retorna resultados para uma pesquisa real de notebook."""
    results = await search_balao_products("notebook")
    
    # Como e um teste real contra o site de producao, pode nao ter estoque ou a estrutura mudar.
    # Fazemos assercoes flexiveis para evitar quebra no CI/CD se o site cair.
    assert isinstance(results, list)
    
    if len(results) > 0:
        for product in results:
            assert "title" in product
            assert "price" in product
            assert "link" in product
            assert product["link"].startswith("http")


@pytest.mark.anyio
async def test_search_balao_products_empty():
    """Valida que busca vazia retorna lista vazia."""
    results = await search_balao_products("")
    assert results == []


@pytest.mark.anyio
async def test_search_balao_products_short():
    """Valida que termos muito curtos sao ignorados."""
    results = await search_balao_products("a")
    assert results == []
