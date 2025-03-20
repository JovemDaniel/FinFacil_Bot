import os
import json
import unicodedata

def carregar_json(caminho):
    if not os.path.exists(caminho):
        return {}
    with open(caminho, "r", encoding="utf-8") as file:
        return json.load(file)

def salvar_json(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as file:
        json.dump(dados, file, indent=4)

def normalize_category(cat: str) -> str:
    norm = ''.join(c for c in unicodedata.normalize('NFD', cat) if unicodedata.category(c) != 'Mn').upper()
    return norm

def is_valid_category(cat: str) -> bool:
    return not cat.replace(',', '').replace('.', '').isdigit()
