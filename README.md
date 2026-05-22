# ABC Leilao Monitor

Ferramenta pessoal para acompanhar apartamentos em leilao no ABC paulista.

O projeto tem duas partes:

- `leilao_monitor.py`: roda a coleta, gera `dados.json`, salva historico e envia alertas.
- `index.html`: painel estatico para abrir no navegador ou publicar no GitHub Pages.

## O que funciona hoje

- Coleta automatica da Caixa quando a pagina publica retorna itens legiveis.
- Gera links de conferencia manual para Caixa, Sold, Portal Zuk, Superbid, Leilao Imovel e Mega Leiloes.
- Gera `dados.json` com `imoveis` confirmados e `links_consulta`.
- Envia WhatsApp via CallMeBot quando configurado.
- Envia e-mail HTML via Gmail quando configurado.
- Roda diariamente as 08:00 pelo GitHub Actions.
- Painel web com filtros, calculadora de custo total, caderno de favoritos e links uteis.
- Aba Guia com modalidades de leilao, sinais de alerta, glossario e fluxo para iniciantes.
- Score explicado por imovel, com motivos de risco e oportunidade.
- Comparacao com historico para marcar oportunidades novas, recorrentes e mudancas de lance.
- Aba Inteligencia com radar de ROI, valor de mercado estimado, lucro potencial, estrategia sugerida e de/para de recursos profissionais.

> Observacao: nem todos os portais permitem scraping confiavel. Por isso o monitor separa dados confirmados de links de conferencia, sem mascarar consulta manual como coleta automatica.

## Arquivos principais

- `leilao_monitor.py`
- `salvar_json.py`
- `index.html`
- `manifest.json`
- `sw.js`
- `requirements.txt`
- `.github/workflows/leilao_diario.yml`
- `tests/test_monitor.py`

## Rodar localmente

1. Instale as dependencias:

```bash
pip install -r requirements.txt
```

2. Opcionalmente copie `.env.example` para `.env` e preencha seus dados.

3. Rode o monitor:

```bash
python leilao_monitor.py
```

4. Sirva a pasta localmente:

```bash
python -m http.server 8000 --bind 127.0.0.1
```

5. Abra `http://127.0.0.1:8000/index.html` no navegador.

Se `dados.json` existir, o painel mostra os dados reais. Se nao existir, mostra dados de demonstracao.

## Configuracao por `.env`

O script carrega automaticamente um arquivo `.env` na raiz do projeto.

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
```

Para desativar alertas locais:

```env
WA_ATIVO=false
EMAIL_ATIVO=false
```

## Configurar no GitHub

1. Crie um repositorio.
2. Suba todos os arquivos deste projeto.
3. Em `Settings > Secrets and variables > Actions`, cadastre:

| Secret | Exemplo |
| --- | --- |
| `WA_NUMERO` | `+5511999999999` |
| `WA_APIKEY` | API Key do CallMeBot |
| `EMAIL_REMETENTE` | `seuemail@gmail.com` |
| `EMAIL_SENHA` | senha de app do Gmail |
| `EMAIL_DEST` | `seuemail@gmail.com` |

4. Em `Actions`, rode `ABC Leilao Monitor - Diario` manualmente para testar.

## Publicar o painel

Ative GitHub Pages apontando para a branch principal. O workflow atualiza `dados.json` e mantem `index.html` publicado.

## Testes

```bash
python -m unittest discover -s tests
```

Os testes cobrem extracao de valores, calculos de imovel, geracao de fontes de consulta e formato do `dados.json`.

## Checklist antes de dar lance

- Leia o edital completo.
- Consulte IPTU na prefeitura.
- Confirme debitos de condominio.
- Consulte matricula no cartorio de registro.
- Verifique ocupacao e prazo de desocupacao.
- Calcule comissao, ITBI, cartorio, reforma e debitos.
- Defina um lance maximo antes do leilao.

Ferramenta pessoal para apoio operacional. Nao constitui assessoria juridica ou financeira.

## Release v0.2

- Nova aba `Guia` para iniciantes.
- Explicacao de modalidades: venda direta, venda online, licitacao aberta, 1a praca, 2a praca e imovel ocupado.
- Glossario rapido de termos essenciais.
- Cards e modal agora mostram motivos do score.
- Relatorio por WhatsApp/e-mail ganhou resumo, dica do dia e score das oportunidades.

## Release v0.3

- Comparacao automatica com o ultimo `historico_*.json`.
- Campo `novo`, `visto_antes` e `mudanca` nos imoveis confirmados.
- Painel mostra quantidade de novidades e selo `Novo`/`Recorrente`.
- Ordenacao por novidades.
- Alertas configuraveis por `ALERTAR_SOMENTE_NOVOS`, `ALERTAR_SCORE_MINIMO` e `ALERTAR_MAX_ITENS`.
- WhatsApp/e-mail informam quantos itens sao novos e quais passaram pelos filtros de alerta.

## Release v0.4

- Analise publica de referencia do Leilao Ninja transformada em recursos originais do monitor.
- Nova aba `Inteligencia` com resumo, radar de oportunidades e de/para funcional.
- Modelo passa a calcular `valor_mercado_estimado`, `lucro_potencial`, `roi_potencial`, `qualidade_localizacao` e `estrategia_sugerida`.
- Cards e modal exibem ROI e leitura financeira alem do score de risco.
- A proposta continua independente: nao copia marca, textos, imagens ou layout de terceiros.
