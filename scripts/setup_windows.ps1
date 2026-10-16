$ErrorActionPreference = "Stop"
Write-Host "Creating project virtual environment..."
python -m venv .venv
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
Write-Host "Installing CPU-only PyTorch..."
& $py -m pip install torch --index-url https://download.pytorch.org/whl/cpu
Write-Host "Installing project dependencies..."
& $py -m pip install -r requirements.txt --no-deps
Write-Host "Checking imports..."
& $py -c "import torch,fastapi,sqlalchemy,boto3,networkx,sklearn; print('DEPENDENCIES_OK'); print('torch=',torch.__version__)"
