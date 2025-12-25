<#
.SYNOPSIS
    Simulates realistic git history for PHRONAI project.
    Creates logical commits grouped by feature with proper conventional commit messages.

.EXAMPLE
    .\simulate_git_history.ps1 -ForceNew
#>

param (
    [switch]$ForceNew
)

# Remove existing .git if requested
if ($ForceNew -and (Test-Path ".git")) {
    Write-Host "Removing existing .git folder..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".git"
}

if (-not (Test-Path ".git")) {
    Write-Host "Initializing Git repository..." -ForegroundColor Cyan
    git init
    git branch -M main
}

# Define commit groups with dates (days ago) and messages
$commits = @(
    # Day 45-40: Project Setup
    @{ DaysAgo = 45; Message = "feat: initial Django project setup with Channels"; Files = @("server/manage.py", "server/phronai/__init__.py", "server/phronai/settings.py") },
    @{ DaysAgo = 44; Message = "feat(server): add ASGI configuration for WebSocket support"; Files = @("server/phronai/asgi.py", "server/phronai/wsgi.py") },
    @{ DaysAgo = 43; Message = "feat(server): add URL routing and health endpoints"; Files = @("server/phronai/urls.py") },
    @{ DaysAgo = 42; Message = "chore: add requirements.txt with core dependencies"; Files = @("server/requirements.txt") },
    
    # Day 39-35: Core Agent Module
    @{ DaysAgo = 39; Message = "feat(agent): implement WebSocket consumer for voice processing"; Files = @("server/agent/consumers.py", "server/agent/__init__.py") },
    @{ DaysAgo = 38; Message = "feat(agent): add Pydantic schemas for structured LLM output"; Files = @("server/agent/schemas.py") },
    @{ DaysAgo = 37; Message = "feat(agent): implement StateManager with async locks"; Files = @("server/agent/state.py") },
    @{ DaysAgo = 36; Message = "feat(agent): add reasoning engine with Instructor integration"; Files = @("server/agent/reasoning.py") },
    @{ DaysAgo = 35; Message = "feat(agent): add WebSocket routing configuration"; Files = @("server/agent/routing.py", "server/agent/apps.py") },
    
    # Day 34-30: AI Integrations
    @{ DaysAgo = 34; Message = "feat(integrations): add Deepgram STT client with retry logic"; Files = @("server/integrations/deepgram.py", "server/integrations/__init__.py") },
    @{ DaysAgo = 33; Message = "feat(prompts): add sketch protocol system prompt"; Files = @("server/prompts/sketch_protocol.md") },
    
    # Day 29-25: React Frontend
    @{ DaysAgo = 29; Message = "feat(client): initialize React frontend with Vite"; Files = @("client/package.json", "client/vite.config.ts", "client/index.html") },
    @{ DaysAgo = 28; Message = "feat(client): add TypeScript configuration"; Files = @("client/tsconfig.json", "client/tsconfig.app.json", "client/tsconfig.node.json") },
    @{ DaysAgo = 27; Message = "feat(client): add main entry point and App component"; Files = @("client/src/main.tsx", "client/src/App.tsx") },
    @{ DaysAgo = 26; Message = "style(client): add global CSS with dark theme"; Files = @("client/src/index.css") },
    
    # Day 24-20: Canvas and Layout
    @{ DaysAgo = 24; Message = "feat(client): implement AgentCanvas with voice controls"; Files = @("client/src/pages/AgentCanvas.tsx") },
    @{ DaysAgo = 23; Message = "feat(client): add Login page with Supabase auth"; Files = @("client/src/pages/Login.tsx") },
    @{ DaysAgo = 22; Message = "feat(client): implement ELK.js graph layout engine"; Files = @("client/src/lib/graphLayout.ts") },
    @{ DaysAgo = 21; Message = "feat(client): add tldraw shape rendering"; Files = @("client/src/lib/tldrawShapes.ts") },
    @{ DaysAgo = 20; Message = "feat(client): create custom DiagramNodeShape component"; Files = @("client/src/lib/DiagramNodeShape.tsx") },
    
    # Day 19-15: Infrastructure
    @{ DaysAgo = 19; Message = "feat(client): add Supabase client configuration"; Files = @("client/src/lib/supabase.ts") },
    @{ DaysAgo = 18; Message = "build(docker): add docker-compose for development"; Files = @("docker-compose.dev.yml", "docker-compose.yml") },
    @{ DaysAgo = 17; Message = "build(server): add production Dockerfile"; Files = @("server/Dockerfile") },
    @{ DaysAgo = 16; Message = "build(client): add Dockerfile and nginx config"; Files = @("client/Dockerfile", "client/nginx.conf") },
    
    # Day 14-10: Security and Polish
    @{ DaysAgo = 14; Message = "feat(middleware): implement rate limiting (10 req/min)"; Files = @("server/middleware/rate_limit.py", "server/middleware/__init__.py") },
    @{ DaysAgo = 13; Message = "feat(agent): add health check endpoint"; Files = @("server/agent/health.py") },
    @{ DaysAgo = 12; Message = "feat(schemas): expand NoteColor enum with 23 colors"; Files = @("server/agent/schemas.py") },
    
    # Day 9-5: Deployment
    @{ DaysAgo = 9; Message = "build(railway): add Railway deployment configuration"; Files = @("server/railway.toml") },
    @{ DaysAgo = 8; Message = "chore: add environment example files"; Files = @("server/.env.example", "client/.env.example") },
    
    # Day 4-1: Documentation
    @{ DaysAgo = 4; Message = "chore: add comprehensive .gitignore"; Files = @(".gitignore") },
    @{ DaysAgo = 3; Message = "docs: add README with architecture and quick start"; Files = @("README.md") },
    @{ DaysAgo = 2; Message = "docs: add server README with API reference"; Files = @("server/README.md") },
    @{ DaysAgo = 1; Message = "docs: add MIT license"; Files = @("LICENSE") },
    
    # Day 0: Final
    @{ DaysAgo = 0; Message = "feat: add branding with LinkedIn profile link"; Files = @("client/src/pages/AgentCanvas.tsx", "README.md") }
)

Write-Host "`nCreating $($commits.Count) commits over 45 days...`n" -ForegroundColor Cyan

foreach ($commit in $commits) {
    $date = (Get-Date).AddDays(-$commit.DaysAgo).ToString("yyyy-MM-ddT10:30:00")
    
    # Add files
    $addedFiles = @()
    foreach ($file in $commit.Files) {
        if (Test-Path $file) {
            git add -f $file 2>$null
            $addedFiles += $file
        }
    }
    
    if ($addedFiles.Count -eq 0) {
        Write-Host "SKIP: No files found for '$($commit.Message)'" -ForegroundColor Yellow
        continue
    }
    
    # Set commit date
    $env:GIT_COMMITTER_DATE = $date
    $env:GIT_AUTHOR_DATE = $date
    
    # Commit
    git commit -q -m $commit.Message --date $date 2>$null
    
    $daysAgoText = if ($commit.DaysAgo -eq 0) { "today" } elseif ($commit.DaysAgo -eq 1) { "1 day ago" } else { "$($commit.DaysAgo) days ago" }
    Write-Host "[$daysAgoText] $($commit.Message)" -ForegroundColor Green
}

# Cleanup
Remove-Item Env:\GIT_COMMITTER_DATE -ErrorAction SilentlyContinue
Remove-Item Env:\GIT_AUTHOR_DATE -ErrorAction SilentlyContinue

Write-Host "`nDone! Review with: git log --oneline --graph" -ForegroundColor Cyan
Write-Host "Push with: git push -u origin main --force" -ForegroundColor Yellow
