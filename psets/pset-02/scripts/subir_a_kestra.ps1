param(
    [string]$BaseUrl = 'http://localhost:8080/api/v1/main',
    [string]$User = 'admin@kestra.io',
    [string]$Password = 'Admin1234',
    [switch]$Execute,
    [int]$BatchId = -1,
    [int]$BatchSize = 1000
)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$auth = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("${User}:${Password}"))
$headers = @{Authorization = "Basic $auth"}
# PowerShell 7: enviar multipart preservando las carpetas del namespace.
foreach ($folder in @('scripts', 'dbt', 'spark', 'kestra')) {
    $files = Get-ChildItem -LiteralPath (Join-Path $root $folder) -File -Recurse |
        Where-Object {
            $_.Extension -in @('.py', '.sql', '.yml', '.json') -and
            $_.FullName -notmatch '[\\/](target|logs|__pycache__|dbt_packages)[\\/]'
        }
    foreach ($file in $files) {
        $relative = [IO.Path]::GetRelativePath($root, $file.FullName).Replace('\', '/')
        $path = [Uri]::EscapeDataString("/$relative")
        Invoke-RestMethod -Method Post -Uri "$BaseUrl/namespaces/pset2/files?path=$path" `
            -Headers $headers -Form @{fileContent = $file} | Out-Null
    }
}
$flow = Get-Content -LiteralPath (Join-Path $root 'kestra/flow_ingesta.yml') -Raw
$exists = $true
try {
    Invoke-RestMethod -Uri "$BaseUrl/flows/pset2/descargar_ai4i" -Headers $headers | Out-Null
} catch {
    if ([int]$_.Exception.Response.StatusCode -eq 404) { $exists = $false } else { throw }
}
if ($exists) {
    Invoke-RestMethod -Method Put -Uri "$BaseUrl/flows/pset2/descargar_ai4i" `
        -Headers $headers -ContentType 'application/x-yaml' -Body ([Text.Encoding]::UTF8.GetBytes($flow)) | Out-Null
} else {
    Invoke-RestMethod -Method Post -Uri "$BaseUrl/flows" -Headers $headers `
        -ContentType 'application/x-yaml' -Body ([Text.Encoding]::UTF8.GetBytes($flow)) | Out-Null
}
Write-Output 'Flow y archivos del namespace actualizados.'
if ($Execute) {
    $execution = Invoke-RestMethod -Method Post `
        -Uri "$BaseUrl/executions/pset2/descargar_ai4i" -Headers $headers `
        -Form @{batch_id = "$BatchId"; batch_size = "$BatchSize"}
    Write-Output "Execution ID: $($execution.id)"
}

