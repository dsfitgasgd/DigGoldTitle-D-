param(
    [ValidatePattern('^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$')]
    [string]$Version = 'dev',
    [ValidatePattern('^[a-z0-9][a-z0-9_-]*$')]
    [string]$Namespace = 'local'
)

$ErrorActionPreference = 'Stop'
$previousTag = $env:IMAGE_TAG
$previousNamespace = $env:DOCKERHUB_NAMESPACE
$previousRevision = $env:VCS_REF
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $revision = git rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read Git revision.' }
    $changes = git status --porcelain
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read Git status.' }
    if ($changes) {
        if ($Version -ne 'dev') {
            throw 'Commit changes before building a release. Use -Version dev for local builds.'
        }
        $revision = "$revision-dirty"
    }
    $env:IMAGE_TAG = $Version
    $env:DOCKERHUB_NAMESPACE = $Namespace
    $env:VCS_REF = $revision
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compose validation failed.' }
    docker compose build
    if ($LASTEXITCODE -ne 0) { throw 'Image build failed.' }
    Write-Host "Built ${Namespace}/diggoldtitle-frontend:${Version}"
    Write-Host "Built ${Namespace}/diggoldtitle-backend:${Version}"
    Write-Host 'No images were pushed.'
}
finally {
    $env:IMAGE_TAG = $previousTag
    $env:DOCKERHUB_NAMESPACE = $previousNamespace
    $env:VCS_REF = $previousRevision
    Pop-Location
}
