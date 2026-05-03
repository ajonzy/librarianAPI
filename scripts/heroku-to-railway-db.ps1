# Requires: Heroku CLI (authenticated), Railway CLI (linked to Postgres service), pg_restore on PATH.
# Run from the librarianAPI repo root:
#   .\scripts\heroku-to-railway-db.ps1 -HerokuApp librarianapi
#
# Set $env:SKIP_RESTORE=1 to only download Heroku backup without restoring.

param(
  [string]$HerokuApp = "librarianapi",
  [string]$DumpPath = "backup.dump"
)

$ErrorActionPreference = "Stop"

Write-Host "Capturing Heroku backup for $HerokuApp ..."
heroku pg:backups:capture --app $HerokuApp
Write-Host "Downloading to $DumpPath ..."
heroku pg:backups:download --app $HerokuApp --output $DumpPath

if ($env:SKIP_RESTORE -eq "1") {
  Write-Host "SKIP_RESTORE=1 set; not running pg_restore."
  exit 0
}

$pgRestoreCmd = Get-Command pg_restore -ErrorAction SilentlyContinue
$pgRestore = if ($pgRestoreCmd) { $pgRestoreCmd.Source } else { $null }
if (-not $pgRestore) {
  Write-Warning "pg_restore not on PATH. Install PostgreSQL client tools (see RAILWAY.md), then run:"
  Write-Warning "  pg_restore --verbose --no-acl --no-owner --clean --if-exists -d `"<DATABASE_PUBLIC_URL>?sslmode=require`" $DumpPath"
  exit 0
}

Write-Host "Reading Railway DATABASE_PUBLIC_URL (link Postgres: railway service link Postgres) ..."
$varsJson = railway variables --json 2>&1 | Out-String
$vars = $varsJson | ConvertFrom-Json
$target = $vars.DATABASE_PUBLIC_URL
if (-not $target) {
  throw "DATABASE_PUBLIC_URL not found in railway variables output."
}

$targetWithSsl = if ($target -match "\?") { "$target&sslmode=require" } else { "$target`?sslmode=require" }

Write-Host "Restoring with pg_restore (warnings are often OK) ..."
& $pgRestore --verbose --no-acl --no-owner --clean --if-exists -d $targetWithSsl $DumpPath
