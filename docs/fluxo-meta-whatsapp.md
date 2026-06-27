# Fluxo Meta + WhatsApp Cloud API

## Objetivo

Configurar a integração oficial da **Balão da Informática Castelo** com:
- Meta Business Manager
- Meta for Developers (App)
- WhatsApp Cloud API (via Meta)

## Fluxo Completo

```
1. Acessar Meta Business Manager
   └─ https://business.facebook.com/
   └─ Login manual do operador
   └─ Verificar Business Account

2. Configurações do Business
   └─ Anotar Business ID
   └─ Verificar conta verificada

3. Meta for Developers
   └─ https://developers.facebook.com/apps/
   └─ Criar App tipo "Business"
   └─ Nomear: "Balão da Informática Castelo"

4. Adicionar produto WhatsApp
   └─ No painel do app → "Adicionar Produto"
   └─ Selecionar WhatsApp
   └─ Associar ao WhatsApp Business Account (WABA)

5. Coletar IDs técnicos (modo sandbox)
   └─ Phone Number ID (número de teste)
   └─ WhatsApp Business Account ID (WABA ID)
   └─ Business ID

6. Testar via Graph Explorer (token temporário)
   └─ Verificar token de usuário
   └─ Testar GET /me/phone_numbers

7. Configurar Webhook (manual)
   └─ URL do webhook: endpoint do sistema de leads
   └─ Verificar token de webhook
   └─ Assinar eventos: messages, message_status

8. Adicionar número real de produção (ação crítica)
   └─ ⚠️ REQUER CHECKPOINT HUMANO
   └─ Registrar número (19) 98751-0267 ou número dedicado
   └─ Verificação via código SMS/chamada

9. Solicitar acesso à API de Produção
   └─ ⚠️ REQUER REVISÃO DO APP
   └─ Preencher formulário de acesso
   └─ Aguardar aprovação do Meta

10. Configurar templates de mensagem
    └─ Criar templates aprovados pelo Meta
    └─ Categorias: MARKETING, UTILITY, AUTHENTICATION
```

## IDs Necessários para Configuração

| Campo | Onde Encontrar | Sensível? |
|-------|---------------|-----------|
| Business ID | Business Settings → rodapé | Não |
| App ID | Painel do App → título | Não |
| Phone Number ID | App → WhatsApp → Getting Started | Não |
| WABA ID | App → WhatsApp → Getting Started | Não |
| App Secret | App → Configurações → Básico | ⚠️ SIM |
| Access Token | Graph Explorer (temporário) | ⚠️ SIM |
| Webhook Token | Sua escolha (aleatório) | ⚠️ SIM |

> **ATENÇÃO**: Dados marcados como sensíveis NUNCA devem ser armazenados em arquivos versionados.

## Ambiente Sandbox vs. Produção

### Sandbox (Testes)
- Número de teste fornecido pelo Meta
- Até 5 números de destinatários de teste
- Sem aprovação necessária
- Limites reduzidos de mensagens

### Produção
- Número real da empresa registrado
- Qualquer número pode receber mensagens
- Requer revisão e aprovação do Meta
- Templates de mensagem precisam ser aprovados

## Referências

- [Documentação WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Getting Started](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started)
- [Phone Numbers](https://developers.facebook.com/docs/whatsapp/cloud-api/phone-numbers)
- [Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)
- [Message Templates](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates)
