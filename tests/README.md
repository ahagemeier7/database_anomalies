Este diretório contém testes iniciais com `pytest`.

Como executar:

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest
pytest -q
```

Observações:
- Os testes usam `monkeypatch` para isolar chamadas ao CRUD.
- Adapte e adicione testes para outros módulos conforme necessário.
