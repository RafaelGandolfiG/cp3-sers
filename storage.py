"""Persistência JSON local para protótipo acadêmico. Não é um backend multiusuário."""

import json
from pathlib import Path

DEFAULT = {
    "clientes": [],
    "residencias": [],
    "equipamentos_catalogo": [
        {
            "id": "E01",
            "nome": "Televisão",
            "categoria": "Eletrônico",
            "potencia_w": 100,
        },
        {
            "id": "E02",
            "nome": "Geladeira",
            "categoria": "Eletrodoméstico",
            "potencia_w": 200,
        },
        {
            "id": "E03",
            "nome": "Ventilador",
            "categoria": "Climatização",
            "potencia_w": 80,
        },
        {
            "id": "E04",
            "nome": "Chuveiro",
            "categoria": "Aquecimento",
            "potencia_w": 5500,
        },
    ],
    "propostas": [],
    "cotacoes": {},
}


def read_db(path):
    p = Path(path)
    if not p.exists():
        return json.loads(json.dumps(DEFAULT))
    d = json.loads(p.read_text(encoding="utf-8"))
    for key, value in DEFAULT.items():
        d.setdefault(key, json.loads(json.dumps(value)))
    return d


def save_db(path, db):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def find(items, code):
    return next((x for x in items if str(x["codigo"]) == str(code)), None)
