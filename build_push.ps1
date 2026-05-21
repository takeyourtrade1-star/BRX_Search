# build_push.ps1 — Build + push ebartex-search to ECR (Windows)
#
# Fixes SSL: AWS CLI on Windows often fails CERTIFICATE_VERIFY_FAILED against ECR.
# Avoids piping to `docker login` (non-TTY / empty password on SSL failure).
#
# Usage:
#   .\build_push.ps1
#   .\build_push.ps1 -NoCache
#   .\build_push.ps1 -Tag v2

param(
    [switch]$NoCache,
    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"
$env:PYTHONWARNINGS = "ignore"

function Invoke-AwsNoVerify {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$AwsArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $out = & aws --no-verify-ssl @AwsArgs 2>&1
    $ErrorActionPreference = $prev
    $lines = @($out | Where-Object {
        $_ -is [string] -and
        $_ -notmatch 'InsecureRequestWarning' -and
        $_ -notmatch 'urllib3' -and
        $_.Trim().Length -gt 0
    })
    if ($lines.Count -eq 0) { return $null }
    return ($lines[-1]).ToString().Trim()
}

$REGION   = "eu-south-1"
$ACCOUNT  = "000876600482"
$REGISTRY = "${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
$REPO     = "ebartex-search"
$IMAGE_LOCAL = "ebartex-search:build"
$IMAGE_ECR   = "${REGISTRY}/${REPO}:${Tag}"

Write-Host ""
Write-Host "=== EBARTEX-SEARCH: verifica AWS ===" -ForegroundColor Cyan
$identity = Invoke-AwsNoVerify sts get-caller-identity --region $REGION
if (-not $identity) {
    Write-Host "ERRORE: AWS CLI non risponde. Esegui: aws configure" -ForegroundColor Red
    exit 1
}
Write-Host "OK $identity" -ForegroundColor Green

Write-Host ""
Write-Host "=== EBARTEX-SEARCH: ECR login (no-verify-ssl) ===" -ForegroundColor Cyan

$token = Invoke-AwsNoVerify ecr get-login-password --region $REGION
if (-not $token -or $token.Length -lt 100) {
    Write-Host "ERRORE: impossibile ottenere token ECR." -ForegroundColor Red
    exit 1
}

$authB64 = [Convert]::ToBase64String([System.Text.Encoding]::ASCII.GetBytes("AWS:$token"))
$dockerConfigPath = Join-Path $env:USERPROFILE ".docker\config.json"
$config = @{
    auths = @{
        $REGISTRY = @{ auth = $authB64 }
    }
}
$config | ConvertTo-Json -Depth 10 | Out-File $dockerConfigPath -Encoding ASCII
Write-Host "OK Docker config aggiornato: $dockerConfigPath" -ForegroundColor Green

Write-Host ""
Write-Host "=== EBARTEX-SEARCH: docker build ===" -ForegroundColor Cyan
$buildArgs = @("build", "-t", $IMAGE_LOCAL, ".")
if ($NoCache) { $buildArgs = @("build", "--no-cache", "-t", $IMAGE_LOCAL, ".") }
& docker @buildArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=== EBARTEX-SEARCH: tag + push ===" -ForegroundColor Cyan
docker tag $IMAGE_LOCAL $IMAGE_ECR
if ($Tag -ne "latest") {
    docker tag $IMAGE_LOCAL "${REGISTRY}/${REPO}:latest"
}

docker push $IMAGE_ECR
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Tag -ne "latest") {
    docker push "${REGISTRY}/${REPO}:latest"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host ""
Write-Host "=== FATTO ===" -ForegroundColor Green
Write-Host "  $IMAGE_ECR"
Write-Host ""
Write-Host "Su EC2 (dopo start_server_v2.sh o pull):" -ForegroundColor Yellow
Write-Host "  docker exec search-api python configure_index.py"
Write-Host "  docker exec search-api python reindex.py"
