"""
Servidor FastAPI local — interface web para o Agente Navegador.

Iniciar:
    python -m agente_navegador.server
    Acesse: http://localhost:8000
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from agente_navegador import __version__
from agente_navegador.collectors import list_plans, load_plan, validate_plan
from agente_navegador.config import config
from agente_navegador.logger import get_logger
from agente_navegador.models import AgentStatus, RunResult

log = get_logger(__name__)

app = FastAPI(
    title="Agente Navegador - Balao da Informatica Castelo",
    description="Agente navegador supervisionado para integracoes Meta/WhatsApp/Instagram/Facebook/TikTok",
    version=__version__,
)

# Estado global simples (para ambiente local/single-user)
_state: Dict[str, Any] = {
    "status": AgentStatus.IDLE,
    "current_plan": None,
    "last_result": None,
    "blocked_actions": [],
    "collected_data": [],
}


# ---------------------------------------------------------------------------
# HTML da interface local — usa substituicao simples (sem .format() para evitar
# conflito com chaves do CSS)
# ---------------------------------------------------------------------------

def _build_html() -> str:
    """Gera o HTML do painel, substituindo placeholders manualmente."""

    plans = list_plans()
    plans_items = "".join(
        f'<li><strong>{p.name}</strong> <span class="badge-small">{p.stat().st_size}b</span></li>'
        for p in plans
    ) or "<li>Nenhum plano encontrado</li>"

    status_obj = _state["status"]
    status_str = status_obj.value if hasattr(status_obj, "value") else str(status_obj)
    status_map = {
        "idle": ("idle", "Aguardando"),
        "running": ("running", "Executando"),
        "waiting_human": ("waiting", "Aguardando Operador"),
        "paused": ("waiting", "Pausado"),
        "finished": ("finished", "Concluido"),
        "error": ("error", "Erro"),
        "blocked": ("blocked", "Bloqueado"),
    }
    status_class, status_label = status_map.get(status_str, ("idle", status_str))

    blocked = _state.get("blocked_actions", [])
    blocked_html = "".join(f"<li>{b}</li>" for b in blocked) or "<li>Nenhuma acao bloqueada</li>"

    collected = _state.get("collected_data", [])
    collected_html = (
        "".join(f'<li><strong>{c["key"]}:</strong> {c["value"]}</li>' for c in collected)
        or "<li>Nenhum dado coletado ainda</li>"
    )

    current_plan = _state.get("current_plan") or "&#8212;"

    html = _HTML_TEMPLATE
    html = html.replace("%%VERSION%%", __version__)
    html = html.replace("%%STATUS%%", status_label)
    html = html.replace("%%STATUS_CLASS%%", status_class)
    html = html.replace("%%CURRENT_PLAN%%", current_plan)
    html = html.replace("%%COLLECTED_COUNT%%", str(len(collected)))
    html = html.replace("%%BLOCKED_COUNT%%", str(len(blocked)))
    html = html.replace("%%PLANS_ITEMS%%", plans_items)
    html = html.replace("%%BLOCKED_HTML%%", blocked_html)
    html = html.replace("%%COLLECTED_HTML%%", collected_html)
    return html


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agente Navegador - Balao da Informatica Castelo</title>
<style>
  :root {
    --red: #e53935;
    --dark: #0d0d0d;
    --card: #1a1a1a;
    --border: #2a2a2a;
    --text: #f0f0f0;
    --muted: #888;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--dark); color: var(--text); font-family: 'Segoe UI', sans-serif; min-height: 100vh; }
  header { background: #111; border-bottom: 2px solid var(--red); padding: 16px 32px; display: flex; align-items: center; gap: 16px; }
  header h1 { font-size: 1.2rem; color: var(--red); font-weight: 700; }
  header span.sub { color: var(--muted); font-size: 0.85rem; }
  .badge { background: var(--red); color: white; padding: 3px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 700; }
  .badge-small { background: #2a2a2a; color: var(--muted); padding: 1px 6px; border-radius: 4px; font-size: 0.72rem; }
  main { max-width: 1100px; margin: 0 auto; padding: 32px 16px; display: grid; gap: 24px; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; }
  .card h2 { font-size: 1rem; color: var(--red); margin-bottom: 16px; }
  .status-pill { display: inline-block; padding: 4px 14px; border-radius: 99px; font-size: 0.8rem; font-weight: 600; }
  .status-idle { background: #333; color: #aaa; }
  .status-running { background: #1a472a; color: #4ade80; }
  .status-waiting { background: #7c2d12; color: #fdba74; }
  .status-finished { background: #1e3a5f; color: #60a5fa; }
  .status-error { background: #450a0a; color: #f87171; }
  .status-blocked { background: #3b0764; color: #c084fc; }
  ul { list-style: none; padding: 0; }
  ul li { padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 0.9rem; color: var(--muted); }
  ul li:last-child { border-bottom: none; }
  ul li strong { color: var(--text); }
  .btn { display: inline-block; padding: 10px 24px; border-radius: 8px; font-weight: 700; font-size: 0.9rem; cursor: pointer; border: none; transition: all 0.2s; text-decoration: none; font-family: inherit; }
  .btn-red { background: var(--red); color: white; }
  .btn-red:hover { background: #c62828; }
  .btn-outline { background: transparent; color: var(--text); border: 1px solid var(--border); }
  .btn-outline:hover { border-color: var(--red); color: var(--red); }
  .btn-group { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
  .endpoint { font-family: monospace; font-size: 0.82rem; color: #60a5fa; }
  footer { text-align: center; padding: 32px; color: var(--muted); font-size: 0.8rem; border-top: 1px solid var(--border); }
</style>
</head>
<body>
<header>
  <div>
    <h1>Agente Navegador Supervisionado</h1>
    <span class="sub">Balao da Informatica Castelo &mdash; Campinas/SP</span>
  </div>
  <span class="badge">v%%VERSION%%</span>
</header>
<main>
  <div class="grid2">
    <div class="card">
      <h2>Status do Agente</h2>
      <p>Status: <span class="status-pill status-%%STATUS_CLASS%%">%%STATUS%%</span></p>
      <ul style="margin-top:16px">
        <li><strong>Plano ativo:</strong> %%CURRENT_PLAN%%</li>
        <li><strong>Dados coletados:</strong> %%COLLECTED_COUNT%%</li>
        <li><strong>Acoes bloqueadas:</strong> %%BLOCKED_COUNT%%</li>
      </ul>
    </div>
    <div class="card">
      <h2>API Endpoints</h2>
      <ul>
        <li><span class="endpoint">GET /health</span> &mdash; Status do servidor</li>
        <li><span class="endpoint">GET /plans</span> &mdash; Lista planos</li>
        <li><span class="endpoint">POST /run-plan</span> &mdash; Inicia execucao</li>
        <li><span class="endpoint">GET /logs</span> &mdash; Lista logs</li>
        <li><span class="endpoint">GET /screenshots</span> &mdash; Lista screenshots</li>
        <li><span class="endpoint">GET /docs</span> &mdash; Swagger UI (FastAPI)</li>
      </ul>
    </div>
  </div>

  <div class="card">
    <h2>Planos Disponiveis</h2>
    <ul>%%PLANS_ITEMS%%</ul>
    <div class="btn-group">
      <a href="/plans" class="btn btn-outline">Ver JSON</a>
      <a href="/docs" class="btn btn-red">API Docs (Swagger)</a>
    </div>
  </div>

  <div class="grid2">
    <div class="card">
      <h2>Acoes Bloqueadas</h2>
      <ul>%%BLOCKED_HTML%%</ul>
    </div>
    <div class="card">
      <h2>Dados Coletados</h2>
      <ul>%%COLLECTED_HTML%%</ul>
    </div>
  </div>

  <div class="card">
    <h2>Controles</h2>
    <p style="color:var(--muted);font-size:0.9rem;margin-bottom:16px">
      Use a <a href="/docs" style="color:var(--red)">API REST (/docs)</a> ou a CLI para controlar o agente.
      Acoes criticas sempre exigem confirmacao humana no terminal.
    </p>
    <p style="color:var(--muted);font-size:0.85rem;background:#111;padding:12px;border-radius:8px;font-family:monospace">
      # Executar plano (no terminal):<br>
      $env:PYTHONIOENCODING="utf-8"<br>
      python -m agente_navegador.cli run plans/meta_whatsapp_setup.yaml --headed
    </p>
    <div class="btn-group">
      <button class="btn btn-red" onclick="runPlan()">Iniciar Plano via API</button>
      <button class="btn btn-outline" onclick="location.reload()">Atualizar Status</button>
      <a href="/logs" class="btn btn-outline">Ver Logs</a>
      <a href="/screenshots" class="btn btn-outline">Screenshots</a>
    </div>
  </div>
</main>
<footer>
  Agente Navegador v%%VERSION%% &mdash; Balao da Informatica Castelo<br>
  Av. Anchieta, 789 &ndash; Campinas/SP | (19) 98751-0267 | www.balao.info
</footer>
<script>
async function runPlan() {
  const name = prompt('Nome do plano (ex: meta_whatsapp_setup):');
  if (!name) return;
  try {
    const r = await fetch('/run-plan', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({plan_name: name, headed: true})
    });
    const d = await r.json();
    alert(JSON.stringify(d, null, 2));
    setTimeout(() => location.reload(), 1000);
  } catch(e) {
    alert('Erro: ' + e.message);
  }
}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root():
    """Interface web do agente navegador."""
    return _build_html()


@app.get("/health", tags=["Sistema"])
async def health():
    """Status do servidor."""
    return {
        "status": "ok",
        "agent_status": _state["status"].value if hasattr(_state["status"], "value") else _state["status"],
        "version": __version__,
        "timestamp": datetime.now().isoformat(),
        "company": config.company_name,
    }


@app.get("/plans", tags=["Planos"])
async def get_plans():
    """Lista todos os planos YAML disponiveis."""
    plans = list_plans()
    return {
        "plans": [
            {
                "name": p.stem,
                "filename": p.name,
                "size_bytes": p.stat().st_size,
            }
            for p in plans
        ]
    }


class RunPlanRequest(BaseModel):
    plan_name: str
    headed: bool = True


@app.post("/run-plan", tags=["Planos"])
async def run_plan_endpoint(request: RunPlanRequest, background_tasks: BackgroundTasks):
    """
    Inicia a execucao de um plano em background.
    NOTA: Para planos com human_checkpoint, use a CLI para interacao completa.
    """
    plan_path = config.plans_dir / f"{request.plan_name}.yaml"
    if not plan_path.exists():
        plan_path = config.plans_dir / f"{request.plan_name}.yml"

    if not plan_path.exists():
        raise HTTPException(status_code=404, detail=f"Plano '{request.plan_name}' nao encontrado.")

    valid, errors = validate_plan(plan_path)
    if not valid:
        raise HTTPException(status_code=422, detail={"errors": errors})

    _state["status"] = AgentStatus.RUNNING
    _state["current_plan"] = request.plan_name

    async def _run():
        from agente_navegador.runner import PlanRunner
        try:
            plan = load_plan(plan_path)
            runner = PlanRunner(plan=plan, headless=not request.headed)
            result = await runner.run()
            _state["status"] = result.status
            _state["last_result"] = result.model_dump()
            _state["blocked_actions"] = result.blocked_actions
            _state["collected_data"] = [c.model_dump() for c in result.collected_data]
        except Exception as exc:
            log.exception(f"Erro ao executar plano via servidor: {exc}")
            _state["status"] = AgentStatus.ERROR

    background_tasks.add_task(_run)

    return {
        "message": f"Plano '{request.plan_name}' iniciado.",
        "note": "Para checkpoints humanos interativos, use a CLI: python -m agente_navegador.cli run",
        "status_url": "/health",
    }


@app.get("/logs", tags=["Sistema"])
async def get_logs():
    """Lista os arquivos de log disponiveis."""
    log_files = sorted(config.log_dir.glob("*.log"), reverse=True)
    return {
        "logs": [
            {
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            }
            for f in log_files[:20]
        ]
    }


@app.get("/screenshots", tags=["Sistema"])
async def get_screenshots():
    """Lista os screenshots gerados."""
    screenshots = sorted(config.screenshot_dir.glob("*.png"), reverse=True)
    return {
        "screenshots": [
            {
                "filename": f.name,
                "size_bytes": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            }
            for f in screenshots[:50]
        ]
    }


@app.get("/status", tags=["Sistema"])
async def get_status():
    """Estado detalhado do agente."""
    return _state


def main() -> None:
    """Ponto de entrada para o servidor."""
    log.info("Iniciando servidor Agente Navegador...")
    log.info("Acesse: http://localhost:8000")
    uvicorn.run(
        "agente_navegador.server:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
