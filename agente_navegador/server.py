"""
Servidor FastAPI local — interface web para o Agente Navegador.

Iniciar:
    python -m agente_navegador.server
    Acesse: http://localhost:8000
"""
from __future__ import annotations

import asyncio
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
    title="Agente Navegador — Balão da Informática Castelo",
    description="Agente navegador supervisionado para integrações Meta/WhatsApp/Instagram/Facebook/TikTok",
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
# HTML da interface local
# ---------------------------------------------------------------------------
_HTML_INTERFACE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agente Navegador — Balão da Informática Castelo</title>
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
  header span { color: var(--muted); font-size: 0.85rem; }
  .badge { background: var(--red); color: white; padding: 2px 10px; border-radius: 99px; font-size: 0.75rem; font-weight: 700; }
  main { max-width: 1100px; margin: 0 auto; padding: 32px 16px; display: grid; gap: 24px; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  @media(max-width:700px){ .grid2{ grid-template-columns:1fr; } }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; }
  .card h2 { font-size: 1rem; color: var(--red); margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
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
  .btn { display: inline-block; padding: 10px 24px; border-radius: 8px; font-weight: 700; font-size: 0.9rem; cursor: pointer; border: none; transition: all 0.2s; }
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
    <h1>🤖 Agente Navegador Supervisionado</h1>
    <span>Balão da Informática Castelo — Campinas/SP</span>
  </div>
  <span class="badge">v{version}</span>
</header>
<main>
  <div class="grid2">
    <div class="card">
      <h2>📡 Status do Agente</h2>
      <p>Status atual: <span class="status-pill status-{status_class}">{status}</span></p>
      <ul style="margin-top:16px">
        <li><strong>Plano ativo:</strong> {current_plan}</li>
        <li><strong>Dados coletados:</strong> {collected_count}</li>
        <li><strong>Ações bloqueadas:</strong> {blocked_count}</li>
      </ul>
    </div>
    <div class="card">
      <h2>🔗 API Endpoints</h2>
      <ul>
        <li><span class="endpoint">GET /health</span> — Status do servidor</li>
        <li><span class="endpoint">GET /plans</span> — Lista planos</li>
        <li><span class="endpoint">POST /run-plan</span> — Inicia execução</li>
        <li><span class="endpoint">GET /logs</span> — Lista logs</li>
        <li><span class="endpoint">GET /screenshots</span> — Lista screenshots</li>
        <li><span class="endpoint">GET /docs</span> — Swagger UI</li>
      </ul>
    </div>
  </div>

  <div class="card">
    <h2>📋 Planos Disponíveis</h2>
    <ul>
      {plans_html}
    </ul>
    <div class="btn-group">
      <a href="/plans" class="btn btn-outline">Ver JSON</a>
      <a href="/docs" class="btn btn-red">📖 API Docs</a>
    </div>
  </div>

  <div class="grid2">
    <div class="card">
      <h2>🚫 Ações Críticas Bloqueadas</h2>
      <ul>
        {blocked_html}
      </ul>
    </div>
    <div class="card">
      <h2>📥 Dados Coletados</h2>
      <ul>
        {collected_html}
      </ul>
    </div>
  </div>

  <div class="card">
    <h2>⚙️ Controles (via API)</h2>
    <p style="color:var(--muted); font-size:0.9rem; margin-bottom:16px">
      Use a <a href="/docs" style="color:var(--red)">API REST (/docs)</a> ou a CLI para controlar o agente.
      Ações críticas sempre exigem confirmação humana no terminal.
    </p>
    <div class="btn-group">
      <button class="btn btn-red" onclick="runPlan()">▶ Iniciar Plano</button>
      <button class="btn btn-outline" onclick="location.reload()">🔄 Atualizar Status</button>
      <a href="/logs" class="btn btn-outline">📜 Ver Logs</a>
      <a href="/screenshots" class="btn btn-outline">📸 Screenshots</a>
    </div>
  </div>
</main>
<footer>
  Agente Navegador v{version} — Balão da Informática Castelo<br>
  Av. Anchieta, 789 – Campinas/SP | (19) 98751-0267 | www.balao.info
</footer>
<script>
async function runPlan() {
  const name = prompt('Nome do plano (ex: meta_whatsapp_setup):');
  if (!name) return;
  const r = await fetch('/run-plan', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({plan_name: name, headed: true})
  });
  const d = await r.json();
  alert(JSON.stringify(d, null, 2));
}
</script>
</body>
</html>"""


def _build_html() -> str:
    plans = list_plans()
    plans_html = "".join(f"<li><strong>{p.name}</strong></li>" for p in plans) or "<li>Nenhum plano encontrado</li>"

    status = _state["status"]
    status_str = status.value if hasattr(status, "value") else str(status)
    status_class_map = {
        "idle": "idle", "running": "running", "waiting_human": "waiting",
        "finished": "finished", "error": "error", "blocked": "blocked", "paused": "waiting",
    }
    status_class = status_class_map.get(status_str, "idle")

    blocked = _state.get("blocked_actions", [])
    blocked_html = "".join(f"<li>{b}</li>" for b in blocked) or "<li>Nenhuma ação bloqueada</li>"

    collected = _state.get("collected_data", [])
    collected_html = "".join(f"<li><strong>{c['key']}:</strong> {c['value']}</li>" for c in collected) or "<li>Nenhum dado coletado ainda</li>"

    return _HTML_INTERFACE.format(
        version=__version__,
        status=status_str,
        status_class=status_class,
        current_plan=_state.get("current_plan") or "—",
        collected_count=len(collected),
        blocked_count=len(blocked),
        plans_html=plans_html,
        blocked_html=blocked_html,
        collected_html=collected_html,
    )


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
    """Lista todos os planos YAML disponíveis."""
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
    Inicia a execução de um plano em background.
    NOTA: Para planos com human_checkpoint, use a CLI para interação completa.
    """
    plan_path = config.plans_dir / f"{request.plan_name}.yaml"
    if not plan_path.exists():
        plan_path = config.plans_dir / f"{request.plan_name}.yml"

    if not plan_path.exists():
        raise HTTPException(status_code=404, detail=f"Plano '{request.plan_name}' não encontrado.")

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
    """Lista os arquivos de log disponíveis."""
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
