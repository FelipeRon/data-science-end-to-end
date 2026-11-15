$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$envPath = Join-Path $root '.env'
if (-not (Test-Path -LiteralPath $envPath)) {
    $lines = Get-Content -LiteralPath (Join-Path $root '.env.example')
    $legacy = Join-Path $root 'kestra/.env.kestra'
    if (Test-Path -LiteralPath $legacy) {
        $match = Get-Content -LiteralPath $legacy |
            Where-Object { $_ -match '^SECRET_SNOWFLAKE_KEY_PASSWORD=' } |
            Select-Object -First 1
        if ($match) {
            $value = ($match -split '=', 2)[1].Trim().Trim('"').Trim("'")
            $lines = $lines -replace '^SNOWFLAKE_PRIVATE_KEY_PASSWORD_B64=.*$', "SNOWFLAKE_PRIVATE_KEY_PASSWORD_B64=$value"
        }
    }
    [IO.File]::WriteAllLines($envPath, $lines, [Text.UTF8Encoding]::new($false))
    Write-Output '.env creado sin imprimir sus secretos.'
} else {
    Write-Output '.env existente conservado.'
}
if (-not (Test-Path -LiteralPath (Join-Path $root 'kestra/pset2_kestra.p8'))) {
    throw 'Falta la clave privada local kestra/pset2_kestra.p8.'
}
New-Item -ItemType Directory -Path (Join-Path $root 'output') -Force | Out-Null

