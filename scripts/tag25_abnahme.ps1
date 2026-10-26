# Fundplatz Tag 25 – lokale Abschlusspruefung fuer Windows PowerShell 5.1+.
# Aufruf bei aktiver (.venv): .\scripts\tag25_abnahme.ps1
$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\manage.py")) {
    Write-Error "Bitte zuerst in C:\Kleinanzeigen wechseln. manage.py fehlt."
    exit 2
}

$originalAsync = $env:FUNDPLATZ_AGENT_ASYNC
$originalLLM = $env:FUNDPLATZ_AGENT_USE_LLM
$ok = $false
try {
    # Fuer reproduzierbare Tests. Im finally-Block alte Werte wiederherstellen.
    $env:FUNDPLATZ_AGENT_ASYNC = "0"
    $env:FUNDPLATZ_AGENT_USE_LLM = "0"

    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $folder = Join-Path (Get-Location) "tag25_reports\$stamp"
    New-Item -ItemType Directory -Path $folder -Force | Out-Null

    $steps = @(
        @{Name="01_django_check"; Arguments=@("manage.py", "check")},
        @{Name="02_migration_check"; Arguments=@("manage.py", "makemigrations", "--check", "--dry-run")},
        @{Name="03_tag25_tests"; Arguments=@("manage.py", "test", "listings.test_day25", "-v", "2", "--noinput")},
        @{Name="04_all_django_tests"; Arguments=@("manage.py", "test", "listings", "--noinput")},
        @{Name="05_agent_tests"; Arguments=@("-m", "unittest", "discover", "-s", "agent_system/tests", "-v")},
        @{Name="06_database_audit"; Arguments=@("manage.py", "fundplatz_audit", "--strict", "--json")}
    )

    $results = @()
    foreach ($step in $steps) {
        $log = Join-Path $folder ($step.Name + ".log")
        Write-Host "`n==> $($step.Name)" -ForegroundColor Cyan
        $arguments = $step.Arguments
        # Windows PowerShell 5.1 kann native stderr-Ausgaben sonst bei "Stop"
        # als terminierenden PowerShell-Fehler behandeln (auch bei Test-OK).
        $priorPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            & python @arguments 2>&1 | Tee-Object -FilePath $log
            $code = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $priorPreference
        }
        if ($null -eq $code) { $code = 1 }
        $results += [pscustomobject]@{Pruefung=$step.Name; ExitCode=$code; Log=$log}
        if ($code -ne 0) {
            Write-Warning "Fehler ($code). Weitere Pruefungen laufen fuer die Diagnose."
        }
    }

    $summary = Join-Path $folder "ABNAHME_ERGEBNIS.txt"
    $results | Format-Table -AutoSize | Out-String | Set-Content -Path $summary -Encoding UTF8
    $ok = @($results | Where-Object { $_.ExitCode -ne 0 }).Count -eq 0
    if ($ok) {
        Add-Content -Path $summary -Value "TECHNISCHE LOKALE PRUEFUNG: OK (keine Produktionsfreigabe)" -Encoding UTF8
        Write-Host "`nTechnische lokale Pruefung: OK." -ForegroundColor Green
    } else {
        Add-Content -Path $summary -Value "TECHNISCHE LOKALE PRUEFUNG: NICHT BESTANDEN" -Encoding UTF8
        Write-Warning "Technische lokale Pruefung: NICHT BESTANDEN."
    }
    Write-Host "Protokolle: $folder"
    Write-Host "WICHTIG: Diese Protokolle nicht oeffentlich ins GitHub-Repository hochladen."
}
finally {
    # Umgebung wieder so herstellen, wie sie vor der Abnahme war.
    if ($null -eq $originalAsync) {
        Remove-Item Env:FUNDPLATZ_AGENT_ASYNC -ErrorAction SilentlyContinue
    } else {
        $env:FUNDPLATZ_AGENT_ASYNC = $originalAsync
    }
    if ($null -eq $originalLLM) {
        Remove-Item Env:FUNDPLATZ_AGENT_USE_LLM -ErrorAction SilentlyContinue
    } else {
        $env:FUNDPLATZ_AGENT_USE_LLM = $originalLLM
    }
}
if (-not $ok) { exit 1 }
exit 0
