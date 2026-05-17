# 🏠 ABC Leilão Monitor — Guia Completo

Ferramenta pessoal gratuita para monitorar apartamentos em leilão no ABC.
Envia alertas diários por **WhatsApp** e **E-mail** automaticamente.

---

## ✅ O que a ferramenta faz

- Busca apartamentos de 70–160k em **Santo André, SBC, Mauá e São Caetano**
- Verifica **Caixa, Sold, Zuk, Superbid e Banco do Brasil** todo dia
- Envia mensagem no **WhatsApp** com os imóveis do dia
- Envia **e-mail HTML** com tabela completa, links e checklist
- Roda automaticamente todo dia às **8h** via GitHub Actions
- **Custo: R$ 0,00**

---

## 🚀 Configuração em 4 passos

### PASSO 1 — Criar conta no GitHub (se não tiver)

1. Acesse [github.com](https://github.com) e crie uma conta gratuita
2. Clique em **New repository**
3. Nome: `leilao-abc-monitor`
4. Marque **Private** (seus dados ficam só com você)
5. Clique em **Create repository**

---

### PASSO 2 — Subir os arquivos

Faça upload de todos estes arquivos no repositório:
- `leilao_monitor.py`
- `requirements.txt`
- `.github/workflows/leilao_diario.yml`

> **Dica:** No GitHub, clique em "uploading an existing file" para subir direto pelo navegador.

---

### PASSO 3 — Configurar o WhatsApp (CallMeBot — gratuito)

1. **Salve** o número `+34 644 44 44 49` na sua agenda (nome: CallMeBot)
2. Abra o WhatsApp e mande esta mensagem exata:
   ```
   I allow callmebot to send me messages
   ```
3. Aguarde a resposta com sua **API Key** (chega em segundos)
4. Anote o número e a API Key — vai precisar no próximo passo

---

### PASSO 4 — Configurar o E-mail (Gmail)

1. Acesse [myaccount.google.com](https://myaccount.google.com)
2. Clique em **Segurança**
3. Ative **Verificação em duas etapas** (obrigatório para continuar)
4. Pesquise por **"Senhas de app"** e clique
5. Em "Selecione o app", escolha **Email** → **Outro** → digite `Leilão Monitor`
6. Clique em **Gerar** — anote a senha de 16 caracteres

---

### PASSO 5 — Adicionar seus dados secretos no GitHub

No seu repositório GitHub:
1. Clique em **Settings** → **Secrets and variables** → **Actions**
2. Clique em **New repository secret** para cada item abaixo:

| Nome do Secret   | Valor                        |
|-----------------|------------------------------|
| `WA_NUMERO`     | `+5511999999999` (seu número)|
| `WA_APIKEY`     | A API Key do CallMeBot       |
| `EMAIL_REMETENTE` | `seuemail@gmail.com`       |
| `EMAIL_SENHA`   | A senha de app de 16 dígitos |
| `EMAIL_DEST`    | `seuemail@gmail.com`         |

---

## ▶️ Testar agora (sem esperar amanhã)

1. No GitHub, clique em **Actions**
2. Clique em **ABC Leilão Monitor — Diário**
3. Clique em **Run workflow** → **Run workflow**
4. Aguarde ~2 minutos
5. Cheque seu WhatsApp e e-mail!

---

## 📱 Exemplo de mensagem WhatsApp que você vai receber

```
🏠 ABC Leilões — 15/06/2025

📌 2 apartamento(s) na faixa 70–160k:

1️⃣ Apartamento 2 quartos, 58m²
📍 Santo André
💰 Lance: R$ 98.000 | Deságio: 38%
✅ Ver edital
🔗 https://venda.caixa.gov.br/...

2️⃣ Apartamento 2 quartos, 65m²
📍 São Bernardo do Campo
💰 Lance: R$ 115.000 | Deságio: 31%
⚠️ Ocupado
🔗 https://www.sold.com.br/...

🔎 Buscar também:
• Sold: https://www.sold.com.br/...
• Zuk: https://www.zuk.com.br/...
• Superbid: https://www.superbid.net/...
• Banco do Brasil: https://leiloes.bb.com.br/...

💡 Lembre-se: leia o edital completo antes de dar o lance!
```

---

## 📋 Checklist antes de dar um lance

Quando encontrar um imóvel interessante, verifique:

- [ ] Leia o **edital completo** no site do leiloeiro
- [ ] Verifique **IPTU atrasado** no portal da prefeitura:
  - Santo André: [santoandre.sp.gov.br](https://santoandre.sp.gov.br)
  - SBC: [saobernardo.sp.gov.br](https://saobernardo.sp.gov.br)
  - Mauá: [maua.sp.gov.br](https://maua.sp.gov.br)
  - São Caetano: [saocaetanodosul.sp.gov.br](https://saocaetanodosul.sp.gov.br)
- [ ] Ligue para o síndico/administradora — **débito de condomínio**
- [ ] Consulte a **matrícula** no Cartório de Registro de Imóveis
- [ ] Verifique se está **ocupado** e qual o prazo de desocupação
- [ ] Defina seu **lance máximo** antes e não passe dele
- [ ] Tenha o dinheiro (caução + valor do lance) **pronto** antes do leilão

---

## 🔧 Personalizando os filtros

Edite o arquivo `leilao_monitor.py`, seção `CONFIG`:

```python
"filtros": {
    "lance_min": 70_000,    # mude o valor mínimo
    "lance_max": 160_000,   # mude o valor máximo
    "tipo": "apartamento",
    "cidades": [            # adicione ou remova cidades
        "Santo André",
        "São Bernardo do Campo",
        "Mauá",
        "São Caetano do Sul",
    ],
    "quartos_min": 2,       # mínimo de quartos
},
```

---

## ❓ Dúvidas frequentes

**Não recebi WhatsApp:**
- Confirme que mandou a mensagem de ativação para o CallMeBot
- Verifique se o número está no formato `+5511999999999`
- Rode o script manualmente pelo GitHub Actions para ver o log de erro

**Não recebi e-mail:**
- Cheque a pasta de Spam
- Confirme que usou a "Senha de App" (não sua senha normal do Gmail)
- A verificação em duas etapas do Google precisa estar ativa

**O script rodou mas não achou imóveis:**
- Sites como Sold e Superbid bloqueiam scrapers; os links de busca são enviados assim mesmo
- A Caixa é a fonte mais confiável para scraping direto
- Verifique se há leilões ativos na região naquele dia

---

*Ferramenta pessoal para uso próprio. Não constitui assessoria jurídica ou financeira.*
