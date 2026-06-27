# 🤖 Agente Navegador Supervisionado

> **Balão da Informática Castelo** — Agente navegador local e supervisionado para configuração de integrações oficiais com Meta Business, WhatsApp Cloud API, Instagram, Facebook e TikTok.

---

## O que é este projeto?

O **Agente Navegador** é uma ferramenta Python que abre o Google Chrome/Chromium de forma **visível** (não invisível), navega pelos painéis oficiais das plataformas Meta, coleta dados técnicos e auxilia na configuração de integrações — tudo sob **supervisão humana total**.

Ele funciona como um **assistente** que:
- Abre o navegador para você
- Navega até as URLs corretas
- Para em checkpoints para você agir manualmente
- Coleta informações técnicas (IDs, URLs)
- Salva screenshots e logs de tudo

---

## Para que serve?

- ✅ Configurar **Meta Business Manager**
- ✅ Criar e configurar app no **Meta for Developers**
- ✅ Configurar **WhatsApp Cloud API** (sandbox e produção)
- ✅ Conectar **Instagram** profissional à Página do Facebook
- ✅ Coletar **Page ID** e dados técnicos da **Página do Facebook**
- ✅ Verificar e configurar app no **TikTok Developers**
- ✅ Guiar **Content Posting API** do TikTok

---

## O que ele faz ✅

- Abre o navegador Chromium de forma visível
- Navega pelas URLs oficiais
- Para em checkpoints para login e ações manuais
- Coleta URLs, textos e atributos de páginas
- Tira screenshots com timestamp
- Salva logs detalhados
- Valida a segurança dos planos YAML
- Bloqueia ações críticas sem checkpoint humano
- Serve uma interface web local em http://localhost:8000

## O que ele NÃO faz ❌

- ❌ Fazer login automaticamente
- ❌ Enviar mensagens automáticas
- ❌ Conectar número WhatsApp sem intervenção humana
- ❌ Publicar conteúdo automaticamente
- ❌ Aceitar termos automaticamente
- ❌ Enviar app para revisão automaticamente
- ❌ Usar WhatsApp Web por QR Code
- ❌ Realizar disparo em massa
- ❌ Armazenar senhas ou tokens sensíveis
- ❌ Operar sem supervisão humana

---

## Empresa

**Balão da Informática Castelo**  
📍 Av. Anchieta, 789 – Campinas/SP  
📱 WhatsApp: (19) 98751-0267  
☎️ Telefone: (19) 3255-1661  
📸 Instagram: [@balaodainformatica_castelo](https://instagram.com/balaodainformatica_castelo)  
🌐 Site: [www.balao.info](https://www.balao.info)

---

## Instalação

### Pré-requisitos

- Python 3.10 ou superior
- Git

### 1. Clone o repositório

```bash
git clone https://github.com/balaocastelo-dev/agente-navegador.git
cd agente-navegador
```

### 2. Crie um ambiente virtual

```bash
python -m venv .venv
```

**Windows:**
```bash
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Instale o Chromium (Playwright)

```bash
playwright install chromium
```

### 5. Configure o ambiente

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edite o `.env` se necessário (os padrões já funcionam).

---

## Como Rodar

### Executar um plano (modo principal)

```bash
# Meta Business + WhatsApp Cloud API
python -m agente_navegador.cli run plans/meta_whatsapp_setup.yaml --headed

# Instagram
python -m agente_navegador.cli run plans/instagram_setup.yaml --headed

# Página do Facebook
python -m agente_navegador.cli run plans/facebook_page_setup.yaml --headed

# TikTok Developers
python -m agente_navegador.cli run plans/tiktok_developers_setup.yaml --headed
```

### Validar um plano (sem executar)

```bash
python -m agente_navegador.cli validate plans/meta_whatsapp_setup.yaml
```

### Listar planos disponíveis

```bash
python -m agente_navegador.cli list-plans
```

### Iniciar o servidor web local

```bash
python -m agente_navegador.server
```

Acesse: **http://localhost:8000**

### Rodar os testes

```bash
pytest -v
```

---

## Planos Disponíveis

| Arquivo | Objetivo |
|---------|----------|
| `plans/meta_whatsapp_setup.yaml` | Meta Business + WhatsApp Cloud API |
| `plans/instagram_setup.yaml` | Instagram Profissional + Graph API |
| `plans/facebook_page_setup.yaml` | Página do Facebook + Page ID |
| `plans/tiktok_developers_setup.yaml` | TikTok Developers + Content Posting API |

---

## Ações Suportadas nos Planos YAML

| Ação | Descrição |
|------|-----------|
| `goto` | Navega para uma URL |
| `click` | Clica em um elemento |
| `fill` | Preenche um campo |
| `wait_for_selector` | Aguarda um elemento aparecer |
| `extract_text` | Extrai texto de um elemento |
| `extract_url` | Captura a URL atual |
| `screenshot` | Tira um screenshot |
| `human_checkpoint` | ⏸ Para e aguarda confirmação humana |
| `collect_input_value` | Coleta valor de um input |
| `collect_attribute` | Coleta atributo HTML |

### Exemplo de Plano YAML

```yaml
name: exemplo
description: Plano de exemplo
steps:
  - action: goto
    url: https://business.facebook.com/

  - action: human_checkpoint
    message: Faça login e confirme para continuar.

  - action: screenshot
    name: home-logado

  - action: extract_url
    save_as: url_atual
```

---

## Segurança

O agente possui um sistema de segurança em duas camadas:

1. **Pré-execução**: Valida o plano inteiro antes de rodar
2. **Runtime**: Verifica cada passo individualmente

### Ações críticas (exigem checkpoint)

- Publicar conteúdo | Enviar mensagem | Conectar número WhatsApp
- Adicionar pagamento | Remover usuário | Excluir app/página
- Aceitar termos | Enviar para revisão | Ativar campanha
- Alterar senha | Gerar token | Baixar dados privados

### Proibições absolutas

- Salvar senha | Armazenar cookies | WhatsApp via QR Code
- Spam / disparo em massa | Burlar autenticação

---

## Estrutura do Projeto

```
agente-navegador/
├── agente_navegador/        ← Código principal
│   ├── cli.py               ← Interface de linha de comando
│   ├── server.py            ← Servidor FastAPI
│   ├── browser.py           ← Gerenciamento do Playwright
│   ├── runner.py            ← Motor de execução de planos
│   ├── supervisor.py        ← Checkpoints humanos
│   ├── safety.py            ← Sistema de segurança
│   ├── collectors.py        ← Carregamento de planos YAML
│   ├── config.py            ← Configurações
│   ├── models.py            ← Modelos Pydantic
│   └── actions/             ← Helpers por plataforma
│       ├── meta_business.py
│       ├── whatsapp_cloud.py
│       ├── instagram.py
│       ├── facebook.py
│       └── tiktok.py
├── plans/                   ← Planos YAML
├── docs/                    ← Documentação
│   ├── preview.html         ← Preview visual do painel
│   ├── seguranca.md         ← Regras de segurança
│   ├── arquitetura.md       ← Arquitetura do sistema
│   └── fluxo-meta-whatsapp.md
├── screenshots/             ← Screenshots gerados
├── logs/                    ← Logs de execução
├── tests/                   ← Testes pytest
├── .env.example             ← Exemplo de configuração
├── requirements.txt         ← Dependências Python
└── pyproject.toml           ← Configuração do projeto
```

---

## Como usar com Meta Business

1. Execute: `python -m agente_navegador.cli run plans/meta_whatsapp_setup.yaml --headed`
2. O navegador abrirá em `https://business.facebook.com/`
3. **Faça login manualmente** quando o agente pausar
4. Confirme no terminal para continuar
5. Siga os checkpoints até coletar todos os IDs

## Como usar com WhatsApp Cloud API

1. Execute o plano `meta_whatsapp_setup.yaml` (já inclui WhatsApp)
2. No checkpoint de "Coletar IDs", anote Phone Number ID e WABA ID
3. Configure o webhook manualmente
4. **NÃO registre o número real** sem revisar os requisitos do Meta

## Como usar com Instagram / Facebook

1. Execute: `python -m agente_navegador.cli run plans/instagram_setup.yaml --headed`
2. Faça login manualmente no Instagram
3. Conecte à Página do Facebook quando o agente orientar
4. Colete o Instagram Business Account ID via Graph Explorer

## Como usar com TikTok

1. Execute: `python -m agente_navegador.cli run plans/tiktok_developers_setup.yaml --headed`
2. Faça login no TikTok Developers manualmente
3. Siga os checkpoints para criar/verificar o app
4. Anote apenas o Client Key (nunca o Client Secret)

---

## Próximos Passos

- [ ] Implementar sistema de webhooks para receber leads
- [ ] Criar painel de leads integrado ao CRM
- [ ] Configurar templates de mensagem aprovados pelo Meta
- [ ] Implementar fluxo de atendimento via WhatsApp Cloud API
- [ ] Integrar Instagram DMs ao sistema de atendimento
- [ ] Configurar TikTok Lead Generation integrado ao CRM

---

## Contribuição

Este projeto é privado da **Balão da Informática Castelo**.  
Para contribuições internas, abra uma issue no repositório.

---

## Licença

MIT License — © 2026 Balão da Informática Castelo
