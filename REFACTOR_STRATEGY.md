# Estrategia de refatoracao

## Objetivo

Evoluir o projeto sem quebrar o monitor diario, mantendo uma fonte de verdade clara, testes verdes e alteracoes pequenas o suficiente para revisar.

## Prioridade 1: estabilizacao

- Manter `python -m unittest discover -s tests` verde antes e depois de cada mudanca.
- Corrigir primeiro bugs que impedem confianca na suite.
- Evitar chamadas reais de rede, WhatsApp ou e-mail em testes automatizados.

## Prioridade 2: fonte de verdade

- Usar a raiz do repositorio como aplicacao principal.
- Manter uma unica versao ativa do codigo para evitar divergencia entre coleta, painel e testes.
- Tratar historico e artefatos gerados como saida do processo, nao como uma segunda copia da aplicacao.

## Prioridade 3: modularizacao do backend

Extrair `leilao_monitor.py` em etapas:

- `config.py`: leitura de `.env` e configuracoes.
- `models.py`: dataclasses e tipos compartilhados.
- `sources/caixa.py`: CSV, HTML fallback e montagem de URLs da Caixa.
- `sources/links.py`: links de conferencia manual.
- `scoring.py`: score, motivos e estrategia sugerida.
- `history.py`: historico, novos, recorrentes e mudancas de preco.
- `notifications.py`: WhatsApp e e-mail.
- `exporters/json_exporter.py`: `dados.json`.
- `main.py`: orquestracao.

Cada extracao deve preservar os testes existentes e ganhar pelo menos um teste de regressao quando alterar comportamento.

## Prioridade 4: frontend

- Corrigir bugs funcionais antes de separar arquivos.
- Depois separar `index.html` em `assets/styles.css` e `assets/app.js`.
- Remover funcoes JavaScript duplicadas, especialmente onde uma definicao sobrescreve outra.
- Manter `dados.json` como contrato estavel entre backend e painel.

## Prioridade 5: operacao

- Workflow deve instalar por `requirements.txt`.
- Gerar `dados.json` mesmo sem imoveis confirmados.
- Salvar historico sempre que a coleta concluir.
- Falha de uma fonte nao deve impedir links de conferencia e alertas restantes.

## Fatias recomendadas

1. Corrigir bugs pequenos e deixar testes verdes.
2. Adicionar mocks para rede/notificacoes.
3. Separar exportacao JSON e historico.
4. Separar fonte Caixa.
5. Separar notificacoes.
6. Corrigir encoding de documentos e UI.
7. Separar frontend em arquivos menores.
