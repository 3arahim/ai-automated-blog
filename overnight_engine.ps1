while ($true) {
    Write-Host "Running overnight automation..."
    
    # Pre-clean dist directory to prevent ghost caching files
    if (Test-Path "astro_blog\dist") {
        Write-Host "Clearing astro_blog/dist..."
        Remove-Item -Recurse -Force "astro_blog\dist\*"
    }

    C:\Python\python.exe generate_articles.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Pushing updates to GitHub..."
        .\push_updates.ps1
    } else {
        Write-Host "Error in run cycle."
    }

    Write-Host "Waiting 30 minutes (1800 seconds) until next loop cycle..."
    Start-Sleep -Seconds 1800
}
