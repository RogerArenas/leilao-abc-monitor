# ABC Leilões — Monitor Pessoal
## Prompt de Contexto do Projeto

> Use este documento para retomar o desenvolvimento em qualquer sessão futura.
> Cole este conteúdo no início da conversa para o assistente entender o projeto completo.

---

## 🎯 Objetivo do Projeto

Ferramenta pessoal e gratuita para monitorar **apartamentos em leilão na região do ABC Paulista**.
O objetivo final é **comprar um apartamento para uso próprio**, sem pagar assessoria, com toda a informação necessária numa tela só.

**Usuário:** Roger Arenas  
**Site publicado:** https://rogerarenas.github.io/leilao-abc-monitor  
**Repositório:** https://github.com/RogerArenas/leilao-abc-monitor  
**Stack:** HTML + CSS + JS puro (sem frameworks) + Python (automação) + GitHub Actions (scheduler) + GitHub Pages (hospedagem)

---

## 🏠 Critérios de Busca do Usuário

| Critério | Valor |
|---|---|
| Tipo | Apartamento |
| Faixa de preço | R$ 70.000 — R$ 160.000 |
| Cidades | Santo André, São Bernardo do Campo, Mauá, São Caetano do Sul |
| Prioridade | Próximo à escola dos filhos em São Caetano do Sul |
| Uso | Moradia própria (não investimento) |

---

## 📁 Estrutura do Projeto

```
leilao-abc-monitor/
├── index.html              # Site completo — interface principal
├── leilao_monitor.py       # Script Python de coleta + alertas
├── salvar_json.py          # Gera dados.json para o site
├── sw.js                   # Service Worker — PWA
├── manifest.json           # Manifest — instalar como app
├── requirements.txt        # Dependências Python
├── .env.example            # Modelo de configuração
├── README.md               # Guia de instalação
└── .github/
    └── workflows/
        └── leilao_diario.yml  # GitHub Actions — roda todo dia às 8h
```

---

## 🖥️ Interface — 5 Abas

### 1. 🔍 Buscar
- Cards de apartamentos com **score de risco** (verde/amarelo/vermelho)
- Filtros: cidade, lance mín/máx, quartos, situação (livre/ocupado), ordenação
- **Busca livre por texto** (bairro, matrícula, cidade)
- Chips de fonte: Caixa, Sold, Zuk, Superbid, BB, D1Lance
- Botão ⭐ para favoritar, ⚖️ para selecionar para comparação
- Barra de comparação fixa no rodapé (até 3 imóveis)
- Modal de **análise completa** com custo total, débitos, score, rota até escola

### 2. 🧮 Calculadora (4 painéis)
- **Custo Real Total** — lance + comissão(5%) + ITBI(3%) + cartório + reforma + débitos
- **Lance Máximo Reverso** — você informa o orçamento, calcula até onde pode dar o lance
- **Financiamento Pós-Arremate** — parcela mensal com sistema Price
- **Valor por m²** — compara lance com mercado (referência ABC: R$3.500–5.500/m²)

### 3. ⭐ Caderno
- **Favoritos salvos** no localStorage usando ID único (não índice — bug corrigido)
- Campo de **anotações livres** por imóvel
- **Checklist de verificação** com barra de progresso (6 itens)
- **Link de rota** até a escola (configurada na aba Alertas)
- Exportar **PDF** com todos os favoritos e checklists
- Botão **Comparar** abre modal com tabela lado a lado

### 4. 🔔 Alertas
- Formulário de **perfil de busca** (min, max, quartos, cidades, endereço da escola)
- Salvo em localStorage — persiste entre sessões
- Gera **links diretos** para configurar alertas gratuitos nas plataformas
- Instruções passo a passo de como cadastrar o alerta em cada site

### 5. 🔗 Sites Reais
- Links verificados e funcionando (Mai/2026)
- Inclui: LeilãoImóvel, Monitor Leilão, Caixa, D1Lance, Sold, Superbid, BB, Grupo Lance, WebLeilões
- Links das **prefeituras** do ABC para consulta de IPTU

---

## ⚙️ Automação — GitHub Actions

```yaml
# Roda todo dia às 8h (horário de Brasília)
cron: '0 11 * * *'
```

**Fluxo completo:**
```
08:00 → Script Python coleta dados
      → Salva dados.json
      → Envia WhatsApp (CallMeBot)
      → Envia E-mail (Gmail SMTP)
      → Git push → GitHub Pages atualiza
      → Site exibe dados do dia
```

**Secrets necessários no GitHub:**
| Secret | Descrição |
|---|---|
| `WA_NUMERO` | Número WhatsApp com DDI (+5511...) |
| `WA_APIKEY` | API Key do CallMeBot (gratuito) |
| `EMAIL_REMETENTE` | Gmail de envio |
| `EMAIL_SENHA` | Senha de App do Gmail (16 dígitos) |
| `EMAIL_DEST` | Gmail de destino |

---

## 🔌 Plataformas Integradas

| Plataforma | Tipo | Status |
|---|---|---|
| **LeilãoImóvel** | Agregador (+400 leiloeiros) | ✅ Links reais |
| **Monitor Leilão** | Agregador com alertas | ✅ Links reais |
| **Caixa Econômica** | Banco oficial | ✅ API pública |
| **D1Lance** | Leiloeiro judicial SP | ✅ Links reais |
| **Sold** | Imóveis bancários | ✅ Links reais |
| **Superbid** | Marketplace leilões | ✅ Links reais |
| **Banco do Brasil** | Banco oficial | ✅ Links reais |
| **Grupo Lance** | Leiloeiro TJ/SP | ✅ Links reais |
| **WebLeilões** | Leiloeiro SP | ✅ Links reais |

---

## 🐛 Bugs Corrigidos

| Bug | Problema | Solução |
|---|---|---|
| Favoritos sumiam | Usava índice do array (`_0, _1`) | Agora usa `_id` único (matrícula + lance + cidade) |
| Filtros resetavam | Não eram persistidos | Salvos em localStorage e restaurados ao abrir |
| Dados sempre demo | Dependia do script Python | Modo demo explícito com aviso claro ao usuário |
| Tipografia desproporcional | Números com 30-32px | Reduzido para 20-22px proporcional |

---

## ✅ Funcionalidades Implementadas

- [x] Busca com filtros completos + busca por texto livre
- [x] Score de risco automático (0-100) com faixa colorida
- [x] Cards com débitos, ocupação, deságio, área, quartos
- [x] Modal de análise completa com custo total detalhado
- [x] Calculadora de custo real total
- [x] Calculadora de lance máximo reverso
- [x] Calculadora de financiamento (sistema Price)
- [x] Calculadora de valor por m² vs mercado
- [x] Caderno de favoritos com ID único (bug corrigido)
- [x] Anotações por imóvel salvas automaticamente
- [x] Checklist de verificação com barra de progresso
- [x] Distância/rota até escola via Google Maps
- [x] Comparador lado a lado (até 3 imóveis)
- [x] Exportar caderno em PDF
- [x] Aba de alertas com perfil de busca salvo
- [x] Links diretos pré-configurados para cada plataforma
- [x] PWA — instalar como app no celular
- [x] Persistência de filtros entre sessões
- [x] Automação diária via GitHub Actions
- [x] Alertas por WhatsApp (CallMeBot)
- [x] Alertas por e-mail (Gmail SMTP)
- [x] GitHub Pages — publicado e acessível

---

## 📋 Checklist do Usuário Antes de Dar um Lance

1. Ler o **edital completo** no site do leiloeiro
2. Consultar **IPTU** na Prefeitura da cidade do imóvel
3. Ligar para **síndico/administradora** — débito de condomínio
4. Verificar **matrícula** no Cartório de Registro de Imóveis
5. Confirmar **situação de ocupação** e prazo de desocupação
6. Definir **lance máximo** antes do leilão e não ultrapassar

---

## 🚀 Próximas Melhorias Possíveis

| Melhoria | Complexidade | Impacto |
|---|---|---|
| Integração real API Caixa no frontend | Média | Alto |
| Notificação push no celular (PWA) | Média | Alto |
| Histórico de preços por bairro | Alta | Médio |
| Mapa com pins dos imóveis | Média | Médio |
| Integração ONR para matrícula automática | Alta | Alto |
| Consulta automática IPTU nas prefeituras | Alta | Alto |

---

## 💻 Como Atualizar o Site

```bash
# Na pasta local do projeto:
git add .
git commit -m "descrição da mudança"
git push
# Em ~2 minutos o site em rogerarenas.github.io atualiza
```

---

## 📱 Como Instalar como App no Celular

**iPhone (Safari):** Abrir o site → Compartilhar → "Adicionar à Tela de Início"  
**Android (Chrome):** Abrir o site → Menu ⋮ → "Adicionar à tela inicial"

---

*Projeto pessoal — não constitui assessoria jurídica ou financeira.*  
*Sempre consulte um advogado antes de participar de leilões imobiliários.*
