# Segurança — Agente Navegador Supervisionado

> **Balão da Informática Castelo** — Este documento descreve as regras de segurança obrigatórias do projeto.

## Princípios Fundamentais

O Agente Navegador foi projetado para operar **sob supervisão humana total**. Isso significa:

1. **Nenhuma ação crítica é automatizada** sem confirmação explícita do operador.
2. **O navegador é sempre visível** (modo headed) para que o operador acompanhe tudo.
3. **Logs e screenshots** registram cada passo para auditoria.
4. **O código não armazena credenciais**, tokens ou cookies sensíveis.

---

## Ações Absolutamente Proibidas

As seguintes ações são **bloqueadas incondicionalmente** pelo `safety.py`, independente de qualquer configuração:

| Ação | Motivo |
|------|--------|
| Salvar senha no navegador | Risco de comprometimento de credenciais |
| Armazenar cookies no repositório | Exposição de sessões ativas |
| WhatsApp Web via QR Code | Não é solução oficial; viola ToS do Meta |
| Disparo em massa / spam | Viola ToS de todas as plataformas |
| Burlar autenticação | Ilegal e viola ToS |
| Subir `.env` para o GitHub | Exposição de dados sensíveis |

---

## Ações Críticas (Exigem Checkpoint Humano)

As seguintes ações **nunca devem ocorrer sem um `human_checkpoint` anterior no plano YAML**:

- Publicar conteúdo
- Enviar mensagem
- Conectar número oficial do WhatsApp
- Adicionar forma de pagamento
- Remover usuário
- Excluir app / página / conta
- Aceitar termos de serviço
- Enviar app para revisão
- Ativar campanha publicitária
- Alterar senha
- Gerar token permanente
- Copiar código 2FA
- Baixar dados privados

---

## Regras para Planos YAML

1. **Todo plano deve ter `human_checkpoint` antes de ações críticas.**
2. A validação de segurança é executada antes da execução (`validate_plan`).
3. A execução é validada em tempo real passo a passo (`check_step_safety`).
4. Se um passo crítico não tiver checkpoint anterior, o agente **bloqueia e para**.

### Exemplo Correto ✅

```yaml
- action: human_checkpoint
  message: Confirme antes de prosseguir.

- action: fill
  selector: "#form"
  value: publicar conteúdo  # ação crítica — precedida por checkpoint
```

### Exemplo Incorreto ❌

```yaml
- action: fill
  selector: "#form"
  value: publicar conteúdo  # BLOQUEADO — sem checkpoint anterior
```

---

## Dados Sensíveis — O Que NUNCA Fazer

- **Não** adicione tokens de API no código fonte
- **Não** salve cookies de sessão no repositório
- **Não** armazene senhas em arquivos YAML
- **Não** faça commit do arquivo `.env`
- **Não** publique chaves de acesso em issues ou PRs

Use variáveis de ambiente (`.env`) ou gerenciadores de segredos para dados sensíveis.

---

## Boas Práticas para Operadores

1. **Sempre revise o plano YAML** antes de executar.
2. **Use `validate` antes de `run`**: `python -m agente_navegador.cli validate plans/...`
3. **Nunca deixe o agente sem supervisão** durante a execução.
4. **Feche o terminal** ao terminar para encerrar o navegador.
5. **Não compartilhe screenshots** que contenham dados sensíveis.
6. **Mantenha o `.env` seguro** e nunca o versione.

---

## Arquitetura de Segurança

```
YAML Plan → load_plan() → validate_plan_safety()
                                    ↓
                          [Bloqueia se crítico sem checkpoint]
                                    ↓
                            PlanRunner.run()
                                    ↓
                    check_step_safety() em CADA passo
                                    ↓
                    human_checkpoint() para interação humana
```

---

## Contato

**Balão da Informática Castelo**  
Av. Anchieta, 789 – Campinas/SP  
(19) 98751-0267 | www.balao.info
