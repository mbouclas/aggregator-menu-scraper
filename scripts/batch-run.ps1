$ErrorActionPreference = "Stop"
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path "C:\work\aggregator-menu-scraper\scraper.log" -Value "`n[$date] Starting scraper script" -Encoding UTF8

try {
    # Auto-detect Python path
    $pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $pythonPath) {
        throw "Python not found in PATH"
    }
    
    # Set UTF-8 environment variables
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"
    
    $process = Start-Process -FilePath $pythonPath `
                             -ArgumentList "batch_scraper.py" `
                             -WorkingDirectory "C:\work\aggregator-menu-scraper" `
                             -NoNewWindow `
                             -RedirectStandardOutput "C:\work\aggregator-menu-scraper\scraper_stdout.log" `
                             -RedirectStandardError "C:\work\aggregator-menu-scraper\scraper_stderr.log" `
                             -PassThru

    $process.WaitForExit()

    # Combine logs with UTF-8 encoding
    Get-Content "C:\work\aggregator-menu-scraper\scraper_stdout.log","C:\work\aggregator-menu-scraper\scraper_stderr.log" -Encoding UTF8 |
        Add-Content -Path "C:\work\aggregator-menu-scraper\scraper.log" -Encoding UTF8

    if ($process.ExitCode -ne 0) {
        Add-Content -Path "C:\work\aggregator-menu-scraper\scraper.log" -Value "`n[$date] Python exited with code $($process.ExitCode)" -Encoding UTF8
        throw "Python script failed."
    } else {
        Add-Content -Path "C:\work\aggregator-menu-scraper\scraper.log" -Value "`n[$date] Script completed OK" -Encoding UTF8
    }
}
catch {
    Add-Content -Path "C:\work\aggregator-menu-scraper\scraper.log" -Value "`n[$date] ERROR: $_" -Encoding UTF8
    throw
}