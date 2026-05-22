# ABC Leilão Monitor

Ferramenta pessoal para acompanhar apartamentos em leilão no ABC paulista.

## Visão geral

O projeto coleta e organiza dados de leilões imobiliários, exibe um painel estático para visualização no navegador e envia alertas por WhatsApp e e-mail quando configurado.

Há duas partes principais:

- `leilao_monitor.py`: coleta dados, gera `dados.json`, salva histórico e envia alertas.
- `index.html`: painel web estático que mostra imóveis, filtros, calculadora, caderno, guia, inteligência e links úteis.

## Funcionalidades

- Coleta automática de dados da Caixa quando a página pública retorna itens legíveis.
- Geração de `dados.json` com imóveis confirmados e `links_consulta` para verificação manual.
- Links de consulta manual para sites como Caixa, Sold, Portal Zuk, Superbid, Leilão Imóvel, Mega Leilões e prefeituras do ABC.
- Envio de alertas por WhatsApp via CallMeBot quando configurado.
- Envio de e-mail HTML via Gmail quando configurado.
- Execução diária às 08:00 via GitHub Actions.
- Painel web com filtros, calculadora de custo total, caderno de favoritos e guia de leilões.
- Aba Guia com modalidades de leilão, sinais de alerta, glossário e fluxo para iniciantes.
- Aba Inteligência com radar de ROI, valor estimado de mercado e análise de potencial.
- Score de risco por imóvel, com motivos de alerta e oportunidades.
- Comparação com histórico para indicar imóveis novos, recorrentes e mudanças de preço.

## Arquivos principais

- `leilao_monitor.py`
- `salvar_json.py`
- `index.html`
- `manifest.json`
- `sw.js`
- `requirements.txt`
- `.env.example`
- `tests/test_monitor.py`
- `.github/workflows/leilao_diario.yml`

## Rodar localmente

1. Instale as dependências:

```bash
pip install -r requirements.txt
```

2. Copie `.env.example` para `.env` e preencha seus dados, se necessário.

3. Rode o monitor:

```bash
python leilao_monitor.py
```

4. Sirva a pasta localmente:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

5. Abra no navegador:

```text
http://127.0.0.1:8000/index.html
```

Se `dados.json` existir, o painel exibe dados reais. Caso contrário, exibe dados de demonstração.

## Configuração via `.env`

Exemplo de variáveis utilizadas pelo projeto:

```env
WA_NUMERO=+5511999999999
WA_APIKEY=SUA_APIKEY_AQUI

EMAIL_REMETENTE=seuemail@gmail.com
EMAIL_SENHA=xxxx xxxx xxxx xxxx
EMAIL_DEST=seuemail@gmail.com

LANCE_MIN=70000
LANCE_MAX=160000
QUARTOS_MIN=2

ALERTAR_SOMENTE_NOVOS=false
ALERTAR_SCORE_MINIMO=0
ALERTAR_MAX_ITENS=5
WA_ATIVO=false
EMAIL_ATIVO=false
```

## GitHub Actions

O projeto pode ser configurado para rodar automaticamente com GitHub Actions. O fluxo de trabalho é:

- coleta de dados diária
- atualização de `dados.json`
- publicação do painel no GitHub Pages

### Segredos recomendados

| Secret | Exemplo |
| --- | --- |
| `WA_NUMERO` | `+5511999999999` |
| `WA_APIKEY` | API Key do CallMeBot |
| `EMAIL_REMETENTE` | `seuemail@gmail.com` |
| `EMAIL_SENHA` | senha de app do Gmail |
| `EMAIL_DEST` | `seuemail@gmail.com` |

## Publicação

Ative o GitHub Pages na branch principal para servir `index.html` como painel público.

## Testes

Execute os testes com:

```bash
python -m unittest discover -s tests
```

Os testes cobrem extração de valores, cálculos de imóvel e formato do JSON.

## Checklist antes de dar lance

- Leia o edital completo.
- Consulte o IPTU na prefeitura.
- Confirme débitos de condomínio.
- Verifique a matrícula no cartório.
- Analise ocupação e prazo de desocupação.
- Calcule comissão, ITBI, cartório, reforma e débitos.
- Defina um lance máximo antes do leilão.

## Observações

- Nem todos os portais permitem scraping confiável.
- O monitor separa dados confirmados de links de conferência.
- A ferramenta oferece apoio operacional, não assessoria jurídica ou financeira.
