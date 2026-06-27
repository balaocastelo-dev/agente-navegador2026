# Arquitetura — Agente Navegador Supervisionado

## Visão Geral

```
┌────────────────────────────────────────────────────────────────┐
│                    Agente Navegador v0.1.0                     │
│                 Balão da Informática Castelo                   │
└────────────────────────────────────────────────────────────────┘
         │                              │
    ┌────▼─────┐                   ┌────▼──────┐
    │  CLI     │                   │  Servidor │
    │ cli.py   │                   │ server.py │
    └────┬─────┘                   └────┬──────┘
         │                              │
         └──────────┬───────────────────┘
                    │
              ┌─────▼──────┐
              │  Runner    │
              │ runner.py  │
              └─────┬──────┘
                    │
       ┌────────────┼────────────┐
       │            │            │
  ┌────▼───┐  ┌────▼────┐  ┌────▼──────┐
  │Browser │  │Supervisor│  │ Safety   │
  │browser │  │supervisor│  │ safety.py│
  │  .py   │  │  .py    │  └──────────┘
  └────┬───┘  └─────────┘
       │
  ┌────▼────────────┐
  │   Playwright    │
  │  (Chromium)     │
  │  Perfil Local   │
  └─────────────────┘
```

## Componentes

### CLI (`cli.py`)
Interface de linha de comando com três comandos:
- `run` — executa um plano YAML
- `validate` — valida estrutura e segurança
- `list-plans` — lista planos disponíveis

### Servidor (`server.py`)
API REST + interface web local (FastAPI + Uvicorn):
- `GET /` — painel HTML
- `GET /health` — status
- `GET /plans` — lista planos
- `POST /run-plan` — inicia execução em background
- `GET /logs` — lista logs
- `GET /screenshots` — lista screenshots

### Motor de Execução (`runner.py`)
Processa os passos de um `Plan` sequencialmente:
1. Valida segurança de cada passo
2. Executa a ação via `browser.py`
3. Aguarda em `human_checkpoint`
4. Salva dados coletados e screenshots

### Navegador (`browser.py`)
Gerencia o Playwright com:
- Perfil persistente local (`browser-profile/`)
- Modo headed (visível) por padrão
- Funções para goto, click, fill, screenshot, extract

### Supervisor (`supervisor.py`)
Gerencia interação humana:
- `human_checkpoint()` — pausa e aguarda confirmação
- `confirm_critical_action()` — confirma ações sensíveis
- `prompt_user()` — solicita entrada do operador

### Segurança (`safety.py`)
Sistema em duas camadas:
1. **Pré-execução**: `validate_plan_safety()` analisa o plano completo
2. **Runtime**: `check_step_safety()` verifica cada passo individualmente

### Modelos (`models.py`)
Pydantic v2:
- `Plan` — estrutura do plano YAML
- `PlanStep` — um passo individual
- `ActionType` — enum de ações suportadas
- `RunResult` — resultado da execução
- `CollectedData` — dados coletados

### Coletores (`collectors.py`)
- `load_plan()` — carrega e valida YAML
- `validate_plan()` — valida estrutura + segurança
- `list_plans()` — lista planos disponíveis

### Configuração (`config.py`)
- Carrega variáveis de `.env` via `python-dotenv`
- Modelo Pydantic com valores padrão seguros
- Instância global `config`

## Fluxo de Execução

```
1. Operador executa:
   python -m agente_navegador.cli run plans/meta_whatsapp_setup.yaml --headed

2. CLI carrega o plano YAML (load_plan)
3. CLI valida segurança do plano (validate_plan_safety)
4. CLI cria PlanRunner e chama runner.run()
5. Runner inicia o navegador Chromium (headed)
6. Para cada passo:
   a. check_step_safety() verifica o passo
   b. Se bloqueado → para e registra
   c. Se human_checkpoint → pausa e aguarda operador
   d. Se ação normal → executa via browser.py
   e. Salva screenshot se configurado
7. Resultado é exibido no terminal
8. Navegador é fechado
```

## Diretórios

```
agente-navegador/
├── agente_navegador/    ← Código Python
│   └── actions/         ← Helpers por plataforma
├── plans/               ← Planos YAML de execução
├── docs/                ← Documentação
├── screenshots/         ← Screenshots gerados (local)
├── logs/                ← Logs de execução (local)
├── tests/               ← Testes pytest
├── browser-profile/     ← Perfil do navegador (.gitignore)
└── .github/workflows/   ← CI/CD
```
