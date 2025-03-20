from utils import carregar_json, salvar_json, normalize_category, is_valid_category
from config import CATEGORIAS_DESPESAS_PATH, DEFAULT_CATEGORIES, CATEGORIAS_ENTRADA_PATH, DEFAULT_CAT_ENTRADA

def get_user_categories(user_id: str) -> list:
    categorias = carregar_json(CATEGORIAS_DESPESAS_PATH)
    if user_id not in categorias:
        categorias[user_id] = DEFAULT_CATEGORIES[:]
        salvar_json(CATEGORIAS_DESPESAS_PATH, categorias)
    else:
        existing = categorias[user_id]
        # Garante que os padrões estejam presentes
        for default_cat in DEFAULT_CATEGORIES:
            if normalize_category(default_cat) not in [normalize_category(c) for c in existing]:
                existing.append(default_cat)
        # Separa padrões e extras
        extras = [cat for cat in existing if normalize_category(cat) not in 
                  [normalize_category(x) for x in DEFAULT_CATEGORIES]]
        extras.sort(reverse=True)
        merged = DEFAULT_CATEGORIES[:] + extras
        categorias[user_id] = merged
        salvar_json(CATEGORIAS_DESPESAS_PATH, categorias)
    cat_list = [c for c in categorias[user_id] if is_valid_category(c)]
    if len(cat_list) != len(categorias[user_id]):
        categorias[user_id] = cat_list
        salvar_json(CATEGORIAS_DESPESAS_PATH, categorias)
    return categorias[user_id]

def update_user_categories(user_id: str, new_list: list):
    categorias = carregar_json(CATEGORIAS_DESPESAS_PATH)
    categorias[user_id] = new_list
    salvar_json(CATEGORIAS_DESPESAS_PATH, categorias)

def get_user_cat_entrada(user_id: str) -> list:
    cat_entrada = carregar_json(CATEGORIAS_ENTRADA_PATH)
    if user_id not in cat_entrada:
        cat_entrada[user_id] = DEFAULT_CAT_ENTRADA[:]
        salvar_json(CATEGORIAS_ENTRADA_PATH, cat_entrada)
    return cat_entrada[user_id]

def update_user_cat_entrada(user_id: str, new_list: list):
    cat_entrada = carregar_json(CATEGORIAS_ENTRADA_PATH)
    cat_entrada[user_id] = new_list
    salvar_json(CATEGORIAS_ENTRADA_PATH, cat_entrada)
