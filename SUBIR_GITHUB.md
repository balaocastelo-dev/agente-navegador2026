# Como Subir no GitHub

## Repositório

**URL:** https://github.com/balaocastelo-dev/agente-navegador

---

## Primeiro Push (repositório vazio)

```bash
# 1. Inicializa o repositório Git (se ainda não foi feito)
git init

# 2. Define a branch principal como main
git branch -M main

# 3. Adiciona todos os arquivos
git add .

# 4. Faz o commit inicial
git commit -m "chore: inicializa agente navegador supervisionado"

# 5. Adiciona o remote do GitHub
git remote add origin https://github.com/balaocastelo-dev/agente-navegador.git

# 6. Faz o push
git push -u origin main
```

---

## Se o repositório já tiver arquivos (pull/rebase antes)

```bash
# Configura o remote (se ainda não foi feito)
git remote add origin https://github.com/balaocastelo-dev/agente-navegador.git

# Faz pull com rebase para evitar conflitos de merge
git pull origin main --rebase

# Adiciona todos os arquivos
git add .

# Faz o commit
git commit -m "chore: inicializa agente navegador supervisionado"

# Faz o push
git push -u origin main
```

---

## Verificar o remote configurado

```bash
git remote -v
```

Saída esperada:
```
origin  https://github.com/balaocastelo-dev/agente-navegador.git (fetch)
origin  https://github.com/balaocastelo-dev/agente-navegador.git (push)
```

---

## O que NÃO subir (já configurado no .gitignore)

- ❌ `.env` — variáveis de ambiente com dados sensíveis
- ❌ `browser-profile/` — perfil do navegador com sessões
- ❌ `.venv/` — ambiente virtual Python
- ❌ `__pycache__/` — cache do Python
- ❌ `*.log` — logs de execução (opcional versionar)
- ❌ Tokens, senhas, chaves de API

---

## Depois do Push — Configurar no GitHub

### 1. Adicionar Secrets (para CI/CD se necessário)

No GitHub: **Settings → Secrets and variables → Actions**

Não há secrets necessários para os testes básicos.

### 2. Verificar o CI/CD

Após o push, o GitHub Actions rodará automaticamente:
- Instala Python 3.10, 3.11, 3.12
- Instala dependências
- Instala Playwright/Chromium
- Roda `pytest`
- Valida os 4 planos YAML

Verifique em: **Actions** → **CI — Agente Navegador**

### 3. Habilitar GitHub Pages (opcional)

Para publicar o preview HTML:
**Settings → Pages → Source: branch main, folder /docs**

Acesse: `https://balaocastelo-dev.github.io/agente-navegador/preview.html`

---

## Atualizações Futuras

Para cada nova atualização:

```bash
git add .
git commit -m "feat: descrição do que foi feito"
git push
```

Convenção de commits recomendada:
- `feat:` — nova funcionalidade
- `fix:` — correção de bug
- `docs:` — documentação
- `chore:` — configuração, deps
- `test:` — testes
- `refactor:` — refatoração

---

## Branches Recomendadas

```
main       ← produção estável
develop    ← desenvolvimento ativo
feat/nome  ← features específicas
fix/nome   ← correções
```

---

## Contato

**Balão da Informática Castelo**  
GitHub: [@balaocastelo-dev](https://github.com/balaocastelo-dev)  
Site: [www.balao.info](https://www.balao.info)
