# 竞赛辅助服务智能体 · 一键启动（Windows PowerShell）
# 用法：在项目根目录执行  .\scripts\start-all.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$VenvPython = Join-Path $Backend ".venv\Scripts\python.exe"
$VenvUvicorn = Join-Path $Backend ".venv\Scripts\uvicorn.exe"
$PipMirror = "https://pypi.tuna.tsinghua.edu.cn/simple"
$NpmMirror = "https://registry.npmmirror.com"

Write-Host "==> 项目根目录: $Root" -ForegroundColor Cyan

function Ensure-Venv {
  if (-not (Test-Path $VenvPython)) {
    Write-Host "==> 创建 Python 虚拟环境..." -ForegroundColor Cyan
    Push-Location $Backend
    python -m venv .venv
    Pop-Location
  }
}

function Ensure-EnvFile {
  $envFile = Join-Path $Backend ".env"
  $example = Join-Path $Backend ".env.example"
  if (-not (Test-Path $envFile)) {
    if (-not (Test-Path $example)) { throw "缺少 backend\.env.example" }
    Copy-Item $example $envFile
    Write-Host "==> 已生成 backend\.env，请填入 LLM_API_KEY 后重新运行本脚本。" -ForegroundColor Yellow
    notepad $envFile
    throw "请先在 .env 中填写 LLM_API_KEY"
  }
  $raw = Get-Content $envFile -Raw
  if ($raw -match "LLM_API_KEY\s*=\s*sk-your-" -or $raw -match "LLM_API_KEY\s*=\s*$") {
    Write-Host "==> 请先编辑 backend\.env，把 LLM_API_KEY 换成真实密钥。" -ForegroundColor Yellow
    notepad $envFile
    throw "LLM_API_KEY 未配置"
  }
}

function Install-Backend {
  Write-Host "==> 安装后端依赖（可重复执行）..." -ForegroundColor Cyan
  & $VenvPython -m pip install -U pip -i $PipMirror | Out-Null
  & $VenvPython -m pip install -r (Join-Path $Backend "requirements.txt") -i $PipMirror
}

function Seed-Data {
  Write-Host "==> 写入样例数据..." -ForegroundColor Cyan
  Push-Location $Backend
  $env:PYTHONPATH = "."
  & $VenvPython scripts\seed_samples.py
  & $VenvPython scripts\seed_ledger.py
  & $VenvPython scripts\seed_team_users.py
  Pop-Location
}

function Install-Frontend {
  Write-Host "==> 安装前端依赖..." -ForegroundColor Cyan
  Push-Location $Frontend
  if (-not (Test-Path "node_modules")) {
    npm install --registry $NpmMirror
  } else {
    Write-Host "    node_modules 已存在，跳过 npm install" -ForegroundColor DarkGray
  }
  Pop-Location
}

Ensure-Venv
Ensure-EnvFile
Install-Backend
Seed-Data
Install-Frontend

Write-Host "==> 启动后端 http://127.0.0.1:8001 ..." -ForegroundColor Green
$backendCmd = "Set-Location '$Backend'; `$env:PYTHONPATH='.'; & '$VenvUvicorn' app.main:app --reload --host 127.0.0.1 --port 8001"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Start-Sleep -Seconds 2

Write-Host "==> 启动前端 http://127.0.0.1:5173 ..." -ForegroundColor Green
$frontendCmd = "Set-Location '$Frontend'; npm run dev -- --host 127.0.0.1 --port 5173"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "完成。请打开浏览器访问：" -ForegroundColor Green
Write-Host "  前端: http://127.0.0.1:5173"
Write-Host "  API : http://127.0.0.1:8001/docs"
Write-Host "演示账号 teacher1 / teacher123 ，学生 stu1 / stu123"
Write-Host "详细说明见 docs\新手部署与使用指南.md"
