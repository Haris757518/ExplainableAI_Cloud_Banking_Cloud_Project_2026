param([ValidateRange(1024,65535)][int]$Port=8000)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$localPython=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$existingPython='D:\ExplainableAI_Cloud_Banking_Cloud_Project_2026_RESEARCH_V1\ExplainableAI_Cloud_Banking_Cloud_Project_2026\.venv\Scripts\python.exe'
if(Test-Path -LiteralPath $localPython){$runtime=$localPython}
elseif(Test-Path -LiteralPath $existingPython){$runtime=$existingPython}
else{$runtime='python'}
Write-Output "Open http://127.0.0.1:$Port after the server starts. Stop with Ctrl+C."
& $runtime -m uvicorn backend.main:app --host 127.0.0.1 --port $Port
