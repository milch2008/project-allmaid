"""Pasta do programa. No .exe (PyInstaller) é a pasta onde está o MaidChan.exe;
rodando como script, é a pasta do projeto. Arquivos editáveis (.env, apps.json, assets) ficam aí."""
import sys
from pathlib import Path

PASTA_APP = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
