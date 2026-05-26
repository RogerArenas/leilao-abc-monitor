# ============================================================
# ABC Leilões — Automação Local (Windows PowerShell)
# Baixa CSV da Caixa, processa e sobe para o GitHub
# Execute: botão direito → "Executar com PowerShell"
# ============================================================

param(
    [switch]$SemGit,      # -SemGit: só baixa e processa, não faz push
    [switch]$ApenasCSV    # -ApenasCSV: só baixa o CSV
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "ABC Leiloes - Atualizacao"

# ── CONFIGURAÇÕES ─────────────────────────────────────────
$LANCE_MIN  = 70000
$LANCE_MAX  = 160000
$CIDADES    = @("SANTO ANDRE", "SAO BERNARDO DO CAMPO", "MAUA", "SAO CAETANO DO SUL")
$PASTA      = Split-Path -Parent $MyInvocation.MyCommand.Path
$CSV_PATH   = Join-Path $PASTA "Lista_imoveis_SP.csv"
$JSON_PATH  = Join-Path $PASTA "dados.json"
$URL_CSV    = "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_SP.csv"

# ── CORES ─────────────────────────────────────────────────
function Ok($msg)   { Write-Host "  ✅ $msg" -ForegroundColor Green }
function Err($msg)  { Write-Host "  ❌ $msg" -ForegroundColor Red }
function Info($msg) { Write-Host "  ℹ  $msg" -ForegroundColor Cyan }
function Warn($msg) { Write-Host "  ⚠  $msg" -ForegroundColor Yellow }

Write-Host ""
Write-Host "══════════════════════════════════════════════" -ForegroundColor DarkCyan
Write-Host "  🏠 ABC LEILÕES — ATUALIZAÇÃO DE DADOS" -ForegroundColor Cyan
Write-Host "  $(Get-Date -Format 'dd/MM/yyyy HH:mm')" -ForegroundColor DarkGray
Write-Host "══════════════════════════════════════════════" -ForegroundColor DarkCyan
Write-Host ""

# ── PASSO 1: BAIXAR CSV DA CAIXA ──────────────────────────
Write-Host "📥 PASSO 1: Baixando CSV da Caixa Econômica..." -ForegroundColor White

$headers = @{
    "User-Agent"      = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    "Accept"          = "text/csv,text/plain,*/*"
    "Accept-Language" = "pt-BR,pt;q=0.9"
    "Referer"         = "https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp"
}

$baixouCSV = $false
try {
    $response = Invoke-WebRequest -Uri $URL_CSV -Headers $headers -OutFile $CSV_PATH -PassThru -TimeoutSec 60
    $tamanho = (Get-Item $CSV_PATH).Length
    Ok "CSV baixado: $([math]::Round($tamanho/1KB, 1)) KB"
    $baixouCSV = $true
} catch {
    Warn "Caixa bloqueou o download automático (403)"
    Info "Abrindo o site manualmente no seu navegador..."
    Start-Process "https://venda-imoveis.caixa.gov.br/listaweb/Lista_imoveis_SP.csv"
    Write-Host ""
    Write-Host "  👆 O download vai iniciar automaticamente no seu navegador." -ForegroundColor Yellow
    Write-Host "     Quando terminar, mova o arquivo CSV para esta pasta:" -ForegroundColor Yellow
    Write-Host "     $PASTA" -ForegroundColor White
    Write-Host ""
    Write-Host "  Pressione ENTER quando o arquivo estiver na pasta..." -ForegroundColor Cyan
    Read-Host | Out-Null
    
    if (Test-Path $CSV_PATH) {
        $tamanho = (Get-Item $CSV_PATH).Length
        Ok "CSV encontrado: $([math]::Round($tamanho/1KB, 1)) KB"
        $baixouCSV = $true
    } else {
        # Procurar CSV em Downloads
        $downloads = "$env:USERPROFILE\Downloads\Lista_imoveis_SP.csv"
        if (Test-Path $downloads) {
            Copy-Item $downloads $CSV_PATH
            Ok "CSV copiado de Downloads"
            $baixouCSV = $true
        } else {
            Err "CSV não encontrado. Execute novamente após baixar o arquivo."
            exit 1
        }
    }
}

if ($ApenasCSV) {
    Ok "CSV disponível em: $CSV_PATH"
    exit 0
}

# ── PASSO 2: PROCESSAR CSV ────────────────────────────────
Write-Host ""
Write-Host "⚙️  PASSO 2: Processando imóveis do ABC..." -ForegroundColor White

# Normalizar nome de cidade para comparação
function NormalizarCidade($cidade) {
    $cidade = $cidade.ToUpper().Trim()
    $cidade = $cidade -replace "Ã", "A" -replace "Á", "A" -replace "É", "E" -replace "Ê", "E"
    $cidade = $cidade -replace "Í", "I" -replace "Ó", "O" -replace "Ô", "O" -replace "Ú", "U"
    $cidade = $cidade -replace "Ç", "C"
    return $cidade
}

# Extrair número de string BR
function ExtrairNumero($texto) {
    if ([string]::IsNullOrEmpty($texto)) { return 0 }
    $clean = $texto -replace "[R$\s]", "" -replace "\.", "" -replace ",", "."
    $num = 0
    if ([double]::TryParse($clean, [ref]$num)) { return [int]$num }
    return 0
}

# Calcular score
function CalcularScore($im) {
    $p = 100
    if ($im.ocupado)                     { $p -= 30 }
    if ($im.praca -eq "2")              { $p -= 10 }
    if ($im.debito_iptu -gt 0)          { $p -= 15 }
    if ($im.debito_cond -gt 0)          { $p -= 10 }
    if ($im.desagio -ge 35)             { $p += 10 }
    if ($im.desagio -lt 20)             { $p -= 10 }
    return [Math]::Max(0, [Math]::Min(100, $p))
}

$imoveis = @()
$totalLinhas = 0
$filtrados = 0

try {
    # Ler CSV com encoding Latin-1 (padrão da Caixa)
    $csv = Import-Csv -Path $CSV_PATH -Delimiter ";" -Encoding Default
    $totalLinhas = $csv.Count
    Info "Total de linhas no CSV: $totalLinhas"

    foreach ($row in $csv) {
        # Filtrar por estado SP
        $uf = ($row.UF ?? $row.Estado ?? "").Trim().ToUpper()
        if ($uf -and $uf -ne "SP") { continue }

        # Filtrar por tipo apartamento
        $tipo = ($row.Tipo ?? $row.'Tipo Imóvel' ?? $row.TipoImovel ?? "").ToLower()
        if ($tipo -notmatch "apto|apartamento") { continue }

        # Filtrar por cidade
        $cidadeCSV = ($row.Cidade ?? $row.Municipio ?? "").Trim()
        $cidadeNorm = NormalizarCidade($cidadeCSV)
        $cidadeMatch = $CIDADES | Where-Object { NormalizarCidade($_) -eq $cidadeNorm }
        if (-not $cidadeMatch) { continue }

        # Valor do lance
        $lanceVal = 0
        foreach ($campo in @("Valor Mínimo de Venda", "Lance Mínimo", "Preco", "Valor")) {
            $v = ExtrairNumero($row.$campo)
            if ($v -gt 0) { $lanceVal = $v; break }
        }
        
        if ($lanceVal -lt $LANCE_MIN -or $lanceVal -gt $LANCE_MAX) { continue }

        # Valor avaliado
        $avaliado = 0
        foreach ($campo in @("Valor de Avaliação", "Avaliacao", "Valor Avaliacao")) {
            $v = ExtrairNumero($row.$campo)
            if ($v -gt 0) { $avaliado = $v; break }
        }
        if ($avaliado -eq 0) { $avaliado = [int]($lanceVal * 1.3) }

        $desagio = if ($avaliado -gt 0) { [int](($avaliado - $lanceVal) / $avaliado * 100) } else { 0 }

        # Dados do imóvel
        $bairro    = ($row.Bairro ?? "").Trim()
        $matricula = ($row.Matricula ?? $row.'Número Imóvel' ?? $row.NumeroImovel ?? "").Trim()
        $area      = ExtrairNumero($row.'Área Total' ?? $row.Area ?? $row.'Area Privativa' ?? "")
        $quartos   = ExtrairNumero($row.Quartos ?? $row.Dormitorios ?? "")
        $endereco  = ($row.Endereço ?? $row.Logradouro ?? "").Trim()
        $praca     = if ($row.Praca -eq "2" -or $row.'2ª Praça' -ne "") { "2" } else { "1" }
        
        # Custos
        $comissao  = [int]($lanceVal * 0.05)
        $itbi      = [int]($lanceVal * 0.03)
        $reforma   = if ($area -gt 0) { $area * 400 } else { 15000 }
        $custoTotal = $lanceVal + $comissao + $itbi + 3500 + $reforma

        # URL do edital
        $urlEdital = if ($matricula) {
            "https://venda-imoveis.caixa.gov.br/sistema/detalhe-imovel.asp?hdnOrigem=index&hdnimovel=$matricula"
        } else {
            "https://venda-imoveis.caixa.gov.br/sistema/busca-imovel.asp"
        }

        $im = [ordered]@{
            titulo       = "Apto $quartos" + "q · " + $area + "m² — $bairro"
            cidade       = $cidadeCSV
            bairro       = $bairro
            lance        = $lanceVal
            avaliado     = $avaliado
            desagio      = $desagio
            fonte        = "Caixa"
            url          = $urlEdital
            praca        = $praca
            ocupado      = $false
            debito_iptu  = 0
            debito_cond  = 0
            area         = $area
            quartos      = $quartos
            matricula    = $matricula
            endereco     = $endereco
            data_leilao  = ($row.'Data Leilão' ?? $row.DataLeilao ?? "Consulte o site")
            custo_total  = $custoTotal
            tipo         = "apartamento"
            _id          = "$matricula-$lanceVal-$cidadeNorm"
        }

        $im.score = CalcularScore($im)
        $imoveis += $im
        $filtrados++
    }

    Ok "Imóveis encontrados na faixa e cidades: $filtrados de $totalLinhas"

} catch {
    Err "Erro ao processar CSV: $_"
    Info "O CSV pode ter um formato diferente do esperado"
    exit 1
}

# ── PASSO 3: SALVAR DADOS.JSON ────────────────────────────
Write-Host ""
Write-Host "💾 PASSO 3: Salvando dados.json..." -ForegroundColor White

$payload = [ordered]@{
    atualizado = Get-Date -Format "dd/MM/yyyy HH:mm"
    total      = $imoveis.Count
    fonte      = "Caixa Econômica Federal — CSV oficial"
    imoveis    = $imoveis
}

$json = $payload | ConvertTo-Json -Depth 10 -Compress:$false
$json | Out-File -FilePath $JSON_PATH -Encoding UTF8

Ok "dados.json salvo com $($imoveis.Count) imóveis"
Info "Arquivo: $JSON_PATH"

# ── PASSO 4: GIT PUSH ─────────────────────────────────────
if (-not $SemGit) {
    Write-Host ""
    Write-Host "🚀 PASSO 4: Enviando para o GitHub..." -ForegroundColor White

    Push-Location $PASTA
    try {
        # Verificar se git está disponível
        $gitOk = $null
        try { $gitOk = git --version 2>&1 } catch {}

        if (-not $gitOk) {
            Warn "Git não encontrado. Instale em https://git-scm.com"
            Info "O dados.json foi gerado localmente. Faça o upload manualmente."
        } else {
            git add dados.json 2>&1 | Out-Null
            $hasChanges = git status --porcelain dados.json
            if ($hasChanges) {
                $commitMsg = "dados: atualização automática $(Get-Date -Format 'dd/MM/yyyy HH:mm')"
                git commit -m $commitMsg 2>&1 | Out-Null
                git push origin main 2>&1 | Out-Null
                Ok "Push realizado! Site atualizando em ~2 minutos"
                Info "https://rogerarenas.github.io/leilao-abc-monitor"
            } else {
                Info "Nenhuma mudança nos dados — push não necessário"
            }
        }
    } catch {
        Warn "Erro no git push: $_"
    }
    Pop-Location
}

# ── RESUMO ────────────────────────────────────────────────
Write-Host ""
Write-Host "══════════════════════════════════════════════" -ForegroundColor DarkCyan
Write-Host "  ✅ CONCLUÍDO!" -ForegroundColor Green
Write-Host "  $($imoveis.Count) apartamentos encontrados no ABC" -ForegroundColor White
if ($imoveis.Count -gt 0) {
    $menor = ($imoveis | Measure-Object -Property lance -Minimum).Minimum
    $maior_desagio = ($imoveis | Measure-Object -Property desagio -Maximum).Maximum
    Write-Host "  Menor lance: R$ $($menor.ToString('N0'))" -ForegroundColor Cyan
    Write-Host "  Maior deságio: $maior_desagio%" -ForegroundColor Cyan
}
Write-Host "══════════════════════════════════════════════" -ForegroundColor DarkCyan
Write-Host ""

# Manter janela aberta
Write-Host "Pressione qualquer tecla para fechar..." -ForegroundColor DarkGray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
