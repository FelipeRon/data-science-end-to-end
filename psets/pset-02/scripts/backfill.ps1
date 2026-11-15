param([int]$BatchSize = 1000, [int]$SourceRows = 10000)
$ErrorActionPreference = 'Stop'
if ($BatchSize -le 0 -or $SourceRows -le 0) { throw 'Tamaños inválidos' }
# concurrency.limit=1 en el flow serializa los lotes y reconstruye las capas por lote.
for ($batch = 0; $batch -lt [Math]::Ceiling($SourceRows / $BatchSize); $batch++) {
    & "$PSScriptRoot/subir_a_kestra.ps1" -Execute -BatchId $batch -BatchSize $BatchSize
}

