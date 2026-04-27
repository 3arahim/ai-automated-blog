Write-Host "Generating AI articles..."
C:\Python\python.exe generate_articles.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Generation successful. Pushing updates..."
    .\push_updates.ps1
    Write-Host "`nSuccess! Your site will be updated shortly at: https://3arahim.github.io/ai-automated-blog/"
} else {
    Write-Host "`nError: Article generation failed."
}
