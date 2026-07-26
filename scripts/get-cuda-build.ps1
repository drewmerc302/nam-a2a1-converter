<#
.SYNOPSIS
Download, verify and assemble the CUDA build of the NAM A2->A1 converter.

.DESCRIPTION
The CUDA build is ~2.6 GiB, and GitHub caps a single release asset at 2 GiB, so the
release carries it as numbered parts (.zip.001, .zip.002, ...). This script fetches the
parts, checks them against the published SHA256SUMS, joins them back into one .zip and
extracts it.

Doing it by hand is also fine -- the parts are a raw byte split, so cmd's built-in
`copy /b a.zip.001 + a.zip.002 a.zip` rebuilds the archive with no extra tooling.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File get-cuda-build.ps1

.EXAMPLE
powershell -ExecutionPolicy Bypass -File get-cuda-build.ps1 -Destination D:\tools -KeepZip
#>
[CmdletBinding()]
param(
    # Where the extracted "nam-a2a1-converter" folder should end up.
    [string]$Destination = (Join-Path $PWD 'nam-a2a1-converter-cuda'),

    # Pull a specific release tag instead of the newest one.
    [string]$Tag = 'latest',

    # Keep the assembled .zip after extracting (default: delete it, it is 2.6 GiB).
    [switch]$KeepZip
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$Repo = 'drewmerc302/nam-a2a1-converter'
$ZipName = 'nam-a2a1-converter-windows-cuda.zip'

function Get-ReleaseAssets {
    $api = if ($Tag -eq 'latest') {
        "https://api.github.com/repos/$Repo/releases/latest"
    } else {
        "https://api.github.com/repos/$Repo/releases/tags/$Tag"
    }
    Write-Host "Querying $api"
    # TLS 1.2 is not the default on stock Windows PowerShell 5.1; without this the API
    # call fails with an unhelpful "could not create SSL/TLS secure channel".
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-RestMethod -Uri $api -Headers @{ 'User-Agent' = 'get-cuda-build' }
}

# The published sums file is `sha256sum` output: "<hash>  <filename>" per line. The first
# line is the ASSEMBLED zip; the rest are the individual parts.
function Read-Sums($path) {
    $map = @{}
    foreach ($line in Get-Content $path) {
        if ($line -match '^\s*([0-9a-fA-F]{64})\s+\*?(.+?)\s*$') {
            $map[[IO.Path]::GetFileName($Matches[2])] = $Matches[1].ToLower()
        }
    }
    return $map
}

function Assert-Hash($path, $expected, $label) {
    if (-not $expected) {
        Write-Warning "no published checksum for $label - skipping verification"
        return
    }
    Write-Host "  verifying $label..." -NoNewline
    $actual = (Get-FileHash $path -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $expected) {
        throw "checksum mismatch for $label`n  expected $expected`n  actual   $actual`nDelete it and re-run; a truncated download is the usual cause."
    }
    Write-Host " ok"
}

$release = Get-ReleaseAssets
Write-Host "Release: $($release.tag_name)"

$parts = @($release.assets | Where-Object { $_.name -match "^$([regex]::Escape($ZipName))\.\d{3}$" } |
           Sort-Object name)
$whole = @($release.assets | Where-Object { $_.name -eq $ZipName })
$sums  = @($release.assets | Where-Object { $_.name -eq "$ZipName.sha256" })

if (-not $parts -and -not $whole) {
    throw "Release $($release.tag_name) has no $ZipName (or parts of it). Assets present:`n  " +
          (($release.assets | ForEach-Object { $_.name }) -join "`n  ")
}

$work = New-Item -ItemType Directory -Force -Path (Join-Path $env:TEMP "nam-cuda-$($release.tag_name)")
$zipPath = Join-Path $work $ZipName

$expected = @{}
if ($sums) {
    $sumPath = Join-Path $work "$ZipName.sha256"
    Invoke-WebRequest -Uri $sums[0].browser_download_url -OutFile $sumPath -UseBasicParsing
    $expected = Read-Sums $sumPath
} else {
    Write-Warning "release publishes no .sha256 - downloads cannot be verified"
}

if ($whole) {
    # Small enough to ship in one piece (a future release might be).
    Write-Host "Downloading $ZipName ($([math]::Round($whole[0].size / 1GB, 2)) GiB)..."
    Invoke-WebRequest -Uri $whole[0].browser_download_url -OutFile $zipPath -UseBasicParsing
    Assert-Hash $zipPath $expected[$ZipName] $ZipName
} else {
    Write-Host "Downloading $($parts.Count) parts ($([math]::Round((($parts | Measure-Object size -Sum).Sum) / 1GB, 2)) GiB total)..."
    $paths = @()
    foreach ($p in $parts) {
        $dest = Join-Path $work $p.name
        # Resume-friendly in the crude sense: an already-correct part is not refetched, so
        # a failed run costs one part rather than the whole 2.6 GiB.
        if ((Test-Path $dest) -and ((Get-Item $dest).Length -eq $p.size) -and
            $expected[$p.name] -and
            ((Get-FileHash $dest -Algorithm SHA256).Hash.ToLower() -eq $expected[$p.name])) {
            Write-Host "  $($p.name) already present and valid"
        } else {
            Write-Host "  $($p.name) ($([math]::Round($p.size / 1MB)) MiB)"
            Invoke-WebRequest -Uri $p.browser_download_url -OutFile $dest -UseBasicParsing
            Assert-Hash $dest $expected[$p.name] $p.name
        }
        $paths += $dest
    }

    Write-Host "Joining $($paths.Count) parts -> $ZipName"
    $out = [IO.File]::Create($zipPath)
    try {
        foreach ($p in $paths) {
            $in = [IO.File]::OpenRead($p)
            try { $in.CopyTo($out) } finally { $in.Dispose() }
        }
    } finally { $out.Dispose() }

    Assert-Hash $zipPath $expected[$ZipName] "assembled $ZipName"
    Remove-Item $paths -Force
}

Write-Host "Extracting to $Destination"
if (Test-Path $Destination) {
    throw "$Destination already exists - remove it or pass -Destination elsewhere."
}
Expand-Archive -Path $zipPath -DestinationPath $Destination -Force

if ($KeepZip) {
    Write-Host "Assembled archive kept at $zipPath"
} else {
    Remove-Item $zipPath -Force
}

$exe = Join-Path $Destination 'nam-a2a1-converter.exe'
Write-Host ""
Write-Host "Done. Launch it with:" -ForegroundColor Green
Write-Host "  $exe"
