import os
from dotenv import load_dotenv

# Define a pasta base do projeto (raiz onde está o bot.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Pasta onde está o .env
CONFIG_DIR = os.path.join(BASE_DIR, "config")
ENV_PATH = os.path.join(CONFIG_DIR, ".env")

# Carrega as variáveis do .env que está na pasta 'config'
load_dotenv(dotenv_path=ENV_PATH)

TOKEN = os.getenv("BOT_TOKEN")

# Criação da pasta 'data' para os arquivos JSON
DATA_DIR = os.path.join(BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Caminhos para os arquivos JSON (dentro da pasta 'data')
DADOS_PATH = os.path.join(DATA_DIR, "dados.json")
DESPESAS_PATH = os.path.join(DATA_DIR, "despesas.json")
CATEGORIAS_DESPESAS_PATH = os.path.join(DATA_DIR, "categorias_despesas.json")
CATEGORIAS_ENTRADA_PATH = os.path.join(DATA_DIR, "categorias_entrada.json")
ENTRADAS_PATH = os.path.join(DATA_DIR, "entradas.json")

# Categorias padrão
DEFAULT_CAT_ENTRADA = ["SALARIO", "EXTRAS"]
DEFAULT_CATEGORIES = ["TRANSPORTE", "MERCADO", "ROUPAS"]

# Estados para fluxo de entradas
(ASK_VALOR, ASK_CAT_ENTRADA, ASK_OBS_ENTRADA, ASK_DATA_ENTRADA) = range(50, 54)

# Estados para relatório de entradas
(REPORT_CAT_ENTRADA, REPORT_DATE_START_ENTRADA, REPORT_DATE_END_ENTRADA) = range(80, 83)

# Estados para fluxo de despesas
(EXPENSE_VALUE, ASK_COMPROVANTE, WAIT_FOR_PHOTO, EXPENSE_CATEGORY, EXPENSE_DATE, EXPENSE_OBS) = range(1, 7)
# Estados para relatório de despesas
(REPORT_CATEGORY, REPORT_DATE_START, REPORT_DATE_END, REPORT_PROV) = range(7, 11)
# Estados para gerenciamento de categorias de despesas
(ADD_CAT, REMOVE_CAT, CONFIRM_REMOVE) = range(11, 14)
# (Opcional) Estado para fluxo de adicionar saldo
ADD_SALDO_VALUE = 14

# Estados para gerenciamento de categorias de entrada
(ADD_CAT_ENTRADA, REMOVE_CAT_ENTRADA, CONFIRM_REMOVE_ENTRADA) = range(60, 63)
