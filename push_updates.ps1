param (
    [string]$CommitMessage = "Add AI-generated articles for $(Get-Date -Format 'yyyy-MM-dd')"
)

Write-Host "Staging files..."
git add .

Write-Host "Committing with message: $CommitMessage"
git commit -m $CommitMessage

Write-Host "Pushing to origin..."
git push origin HEAD

Write-Host "Operation complete!"
