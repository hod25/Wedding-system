<#!
.SYNOPSIS
  Generates a strong BOT_API_KEY and optionally appends or creates a local .env file.

.DESCRIPTION
  Uses .NET cryptography to produce a 32-byte random key (64 hex chars). You can specify a different length.

.PARAMETER Bytes
  Number of random bytes (default 32). Final hex string length = Bytes*2.

.PARAMETER Append
  If provided, will create .env if missing and add/replace BOT_API_KEY line.

.EXAMPLE
  ./scripts/generate_bot_key.ps1

.EXAMPLE
  ./scripts/generate_bot_key.ps1 -Bytes 48 -Append
#>
param(
    [int]$Bytes = 32,
    [switch]$Append
)

if ($Bytes -lt 16) { Write-Error 'Minimum 16 bytes recommended'; exit 1 }

$bytesArr = New-Object byte[] $Bytes
[System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytesArr)
$key = ($bytesArr | ForEach-Object { $_.ToString('x2') }) -join ''

Write-Host "Generated BOT_API_KEY: $key" -ForegroundColor Green

if ($Append) {
    $envPath = Join-Path -Path (Get-Location) -ChildPath '.env'
    if (-not (Test-Path $envPath)) {
        Set-Content -Path $envPath -Value "BOT_API_KEY=$key" -Encoding UTF8
        Write-Host ".env created with BOT_API_KEY" -ForegroundColor Yellow
    } else {
        $lines = Get-Content $envPath
        $other = $lines | Where-Object { -not ($_ -match '^BOT_API_KEY=') }
        $other + "BOT_API_KEY=$key" | Set-Content -Path $envPath -Encoding UTF8
        Write-Host "BOT_API_KEY updated in existing .env" -ForegroundColor Yellow
    }
}
