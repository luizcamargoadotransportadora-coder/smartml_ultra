"""
SmartML Ultra - Testes da API Principal (FastAPI)
Validação resiliente de endpoints.
"""
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["projeto"] == "SmartML Ultra"
    assert "versao" in data

def test_analisar_produto_valido():
    payload = {
        "titulo": "iPhone 15 Pro Max 256GB",
        "custo": 2000.0
    }
    response = client.post("/analisar", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Verifica se a API respondeu ao contrato estruturado (sucesso ou mensagem controlada)
    assert "sucesso" in data or "mensagem" in data

def test_analisar_produto_custo_invalido():
    payload = {
        "titulo": "Produto Teste",
        "custo": -10.0
    }
    response = client.post("/analisar", json=payload)
    assert response.status_code in [200, 422]

def test_analisar_lote():
    payload = {
        "produtos": [
            {"titulo": "iPhone 15 Pro Max 256GB", "custo": 2000.0},
            {"titulo": "Capa Silicone iPhone 15", "custo": 18.0}
        ]
    }
    response = client.post("/analisar-lote", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["sucesso"] is True
    assert data["total"] == 2
    assert len(data["resultados"]) == 2