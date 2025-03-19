import os
import json
import logging
import unicodedata
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, CallbackContext, ConversationHandler,
    MessageHandler, filters
)

# Carrega variáveis do .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Configuração do Logger
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Arquivos de dados
DADOS_PATH = "dados.json"         # Saldos dos usuários
DESPESAS_PATH = "despesas.json"   # Despesas registradas
CATEGORIAS_PATH = "categorias.json" # Categorias dos usuários
CATEGORIAS_ENTRADA_PATH = "categorias_entrada.json"  # novo arquivo p/ categorias de entrada
ENTRADAS_PATH = "entradas.json"     # Entradas (adição de saldo)
DEFAULT_CAT_ENTRADA = ["SALARIO", "EXTRAS"]

# Estados para fluxo de entradas (exemplo)
(ASK_VALOR, ASK_CAT_ENTRADA, ASK_OBS_ENTRADA, ASK_DATA_ENTRADA) = range(50, 54)

# Estados para relatório de entradas
(REPORT_CAT_ENTRADA, REPORT_DATE_START_ENTRADA, REPORT_DATE_END_ENTRADA) = range(80, 83)

# Categorias padrão para novos usuários
DEFAULT_CATEGORIES = ["TRANSPORTE", "MERCADO", "ROUPAS"]

# Estados para fluxo de despesas
(EXPENSE_VALUE, ASK_COMPROVANTE, WAIT_FOR_PHOTO, EXPENSE_CATEGORY, EXPENSE_DATE, EXPENSE_OBS) = range(1, 7)
# Estados para fluxo de relatórios
(REPORT_CATEGORY, REPORT_DATE_START, REPORT_DATE_END, REPORT_PROV) = range(7, 11)
# Estados para gerenciamento de categorias (adicionar e remover)
(ADD_CAT, REMOVE_CAT, CONFIRM_REMOVE) = range(11, 14)
# Estado para fluxo de adicionar saldo
ADD_SALDO_VALUE = 14

# --- Funções utilitárias para JSON ---
def carregar_json(caminho):
    if not os.path.exists(caminho):
        return {}
    with open(caminho, "r", encoding="utf-8") as file:
        return json.load(file)

def salvar_json(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as file:
        json.dump(dados, file, indent=4)

# Normaliza string removendo acentos e convertendo para maiúsculas
def normalize_category(cat: str) -> str:
    norm = ''.join(c for c in unicodedata.normalize('NFD', cat) if unicodedata.category(c) != 'Mn').upper()
    return norm

def is_valid_category(cat: str) -> bool:
    return not cat.replace(',', '').replace('.', '').isdigit()

# Retorna a lista de categorias do usuário (cria se não existir)
def get_user_categories(user_id: str) -> list:
    categorias = carregar_json(CATEGORIAS_PATH)
    if user_id not in categorias:
        categorias[user_id] = DEFAULT_CATEGORIES[:]
        salvar_json(CATEGORIAS_PATH, categorias)
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
        salvar_json(CATEGORIAS_PATH, categorias)
    cat_list = [c for c in categorias[user_id] if is_valid_category(c)]
    if len(cat_list) != len(categorias[user_id]):
        categorias[user_id] = cat_list
        salvar_json(CATEGORIAS_PATH, categorias)
    return categorias[user_id]

def update_user_categories(user_id: str, new_list: list):
    categorias = carregar_json(CATEGORIAS_PATH)
    categorias[user_id] = new_list
    salvar_json(CATEGORIAS_PATH, categorias)

# --- Comandos Básicos ---
async def start(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    dados = carregar_json(DADOS_PATH)
    comandos = (
        "📌 Comandos disponíveis:\n\n"
        "• /start - Iniciar bot\n"
        "• /ajuda - Ver comandos\n"
        "• /entradas - Menu de entradas\n"
        "• /despesas - Menu de despesas\n"
        "• /relatorios - Gerar relatório de despesas\n"
        "• /cancelar - Cancelar operação atual"
    )

    if user_id in dados:
        msg = (
            "Que bom te ver novamente! 🎉\n"
            "Seja bem-vindo ao FinFacil_Bot. 💰\n\n"
            f"{comandos}"
        )
    else:
        msg = (
            "Olá! Eu sou o FinFacil_Bot. 🏦💰\n\n"
            "Sou seu assistente financeiro virtual.\n\n"
            f"{comandos}"
        )

    # Teclado principal
    main_keyboard = [
        ['/entradas', '/adicionar_saldo'],
        ['/despesas', '/relatorios'],
        ['/ajuda', '/cancelar']
    ]
    reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)

    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)

async def ajuda(update: Update, context: CallbackContext) -> None:
    main_keyboard = [
        ['/entradas', '/adicionar_saldo'],
        ['/despesas', '/relatorios'],
        ['/ajuda', '/cancelar']
    ]
    reply_markup = ReplyKeyboardMarkup(main_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "📌 <b>Comandos disponíveis:</b>\n\n"
        "• /start - Iniciar bot\n"
        "• /ajuda - Ver comandos\n"
        "• /entradas - Menu de Entradas\n"
        "• /despesas - Menu de despesas\n"
        "• /relatorios - Gerar relatório de despesas\n"
        "• /cancelar - Cancelar operação atual",
        parse_mode="HTML",
        reply_markup=reply_markup
    )

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

# -----------------------------
# Menu SALDO
# -----------------------------
async def saldo_menu(update: Update, context: CallbackContext):
    # Menu de opções
    msg = (
        "💰 <b>Menu de Entradas:</b>\n\n"
        "• /consultar_saldo - Ver saldo atual\n"
        "• /adicionar_saldo - Adicionar entrada de saldo\n"
        "• /listar_cat_entrada - Listar categorias de entrada\n"
        "• /adicionar_cat_entrada - Adicionar categoria de entrada\n"
        "• /remover_cat_entrada - Remover categoria de entrada\n"
        "• /voltar - Voltar ao menu principal"
    )
    keyboard = [
        ['/consultar_saldo', '/adicionar_saldo'],
        ['/listar_cat_entrada', '/adicionar_cat_entrada'],
        ['/remover_cat_entrada', '/voltar']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)

async def consultar_saldo(update: Update, context: CallbackContext):
    dados = carregar_json("dados.json")
    user_id = str(update.message.from_user.id)
    saldo_usuario = dados.get(user_id, 0)
    await update.message.reply_text(f"💰 Seu saldo atual é: R$ {saldo_usuario:.2f}")

# -----------------------------
# Fluxo Adicionar Saldo (com categorias de entrada)
# -----------------------------
async def adicionar_saldo_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Qual valor deseja adicionar ao saldo? Ex: 300 ou 300,50")
    return ASK_VALOR

async def ask_valor_saldo(update: Update, context: CallbackContext):
    valor_str = update.message.text.replace(',', '.')
    try:
        valor = float(valor_str)
        if valor <= 0:
            await update.message.reply_text("❌ O valor precisa ser maior que 0. Tente novamente:")
            return ASK_VALOR
    except ValueError:
        await update.message.reply_text("❌ Valor inválido. Digite um número, ex: 300,00")
        return ASK_VALOR

    context.user_data["valor_entrada"] = valor
    # Pergunta a categoria de entrada
    user_id = str(update.message.from_user.id)
    cat_list = get_user_cat_entrada(user_id)

    # Teclado com categorias de entrada + '/cancelar'
    keyboard = [[cat] for cat in cat_list]
    keyboard.append(['/cancelar'])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Escolha a categoria desta entrada:\n" + "\n".join(sorted(cat_list)),
        reply_markup=reply_markup
    )

    return ASK_CAT_ENTRADA

async def ask_cat_entrada(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    cat_list = get_user_cat_entrada(user_id)

    cat_escolhida = update.message.text.strip()
    if cat_escolhida.upper() == "/CANCELAR":
        await update.message.reply_text("Operação cancelada.")
        return ConversationHandler.END

    # Normaliza a entrada do usuário
    cat_escolhida_norm = normalize_category(cat_escolhida)

    # Monta uma lista normalizada das categorias existentes
    cat_list_norm = [normalize_category(c) for c in cat_list]

    # Verifica se a versão normalizada do que o usuário digitou existe na lista normalizada
    if cat_escolhida_norm not in cat_list_norm:
        await update.message.reply_text("Categoria inválida! Tente novamente ou /cancelar.")
        return ASK_CAT_ENTRADA

    # Caso seja válida, encontramos a categoria "original" (com acentos, etc.)
    # para armazenar exatamente como está no JSON
    for original_cat in cat_list:
        if normalize_category(original_cat) == cat_escolhida_norm:
            context.user_data["cat_entrada"] = original_cat
            break

    await update.message.reply_text("Digite uma observação para esta entrada ou 'NADA' para pular:")
    return ASK_OBS_ENTRADA

async def ask_obs_entrada(update: Update, context: CallbackContext):
    obs = update.message.text.strip()
    if obs.upper() == "NADA":
        obs = ""
    context.user_data["obs_entrada"] = obs
    await update.message.reply_text("Digite a data da entrada (dd/mm/yyyy) ou /cancelar:")
    return ASK_DATA_ENTRADA

async def ask_data_entrada(update: Update, context: CallbackContext):
    data_text = update.message.text.strip()
    if data_text.upper() == "/CANCELAR":
        await update.message.reply_text("Operação cancelada.")
        return ConversationHandler.END

    try:
        data_obj = datetime.strptime(data_text, "%d/%m/%Y")
    except ValueError:
        await update.message.reply_text(
            "Data inválida! Use o formato dd/mm/yyyy ou /cancelar."
        )
        return ASK_DATA_ENTRADA

    # Verifica se a data é futura
    if data_obj > datetime.now():
        await update.message.reply_text(
            "⚠️ A data não pode ser futura. \n\n<b>Informe uma data válida (dd/mm/yyyy):</b>",
            parse_mode="HTML"
        )
        return ASK_DATA_ENTRADA

    # Se chegar aqui, a data é válida e não é futura
    context.user_data["data_entrada"] = data_obj.strftime("%d/%m/%Y")

    # Agora atualiza o saldo e mostra o resultado
    user_id = str(update.message.from_user.id)
    dados = carregar_json(DADOS_PATH)
    saldo_atual = dados.get(user_id, 0)

    valor = context.user_data["valor_entrada"]
    novo_saldo = saldo_atual + valor
    dados[user_id] = novo_saldo
    salvar_json(DADOS_PATH, dados)

    # Salva a entrada em entradas.json (conforme snippet anterior)
    entradas = carregar_json("entradas.json")
    if user_id not in entradas:
        entradas[user_id] = []
    existing_ids = [e.get("id", 0) for e in entradas[user_id]]
    new_id = max(existing_ids, default=0) + 1

    nova_entrada = {
        "id": new_id,
        "valor": valor,
        "categoria": context.user_data["cat_entrada"],
        "data": context.user_data["data_entrada"],
        "observacao": context.user_data["obs_entrada"],
    }
    entradas[user_id].append(nova_entrada)
    salvar_json("entradas.json", entradas)

    msg = (
        f"✅ Entrada registrada!\n"
        f"Valor: R$ {valor:.2f}\n"
        f"Categoria: {context.user_data['cat_entrada']}\n"
        f"Data: {context.user_data['data_entrada']}\n"
        f"Obs: {context.user_data['obs_entrada']}\n\n"
        f"💰 Novo saldo: R$ {novo_saldo:.2f}"
    )
    await update.message.reply_text(msg)
    await ajuda(update, context)
    return ConversationHandler.END

# -----------------------------
# Gerenciamento de categorias de entrada
# -----------------------------
(ADD_CAT_ENTRADA, REMOVE_CAT_ENTRADA, CONFIRM_REMOVE_ENTRADA) = range(60, 63)

async def listar_cat_entrada(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    cat_list = get_user_cat_entrada(user_id)
    msg = "📂 <b>Suas categorias de entrada:</b>\n" + "\n".join(sorted(cat_list))
    await update.message.reply_text(msg, parse_mode="HTML")

async def adicionar_cat_entrada_cmd(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    cat_list = get_user_cat_entrada(user_id)
    msg = (
        "📥 <b>Digite o nome da categoria de entrada a adicionar:</b>\n\n"
        "Suas categorias atuais:\n" + "\n".join(sorted(cat_list))
    )
    await update.message.reply_text(msg, parse_mode="HTML")
    return ADD_CAT_ENTRADA

async def process_add_cat_entrada(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    cat_list = get_user_cat_entrada(user_id)

    nova_cat = update.message.text.strip()
    nova_cat_norm = normalize_category(nova_cat)
    if nova_cat_norm in [normalize_category(c) for c in cat_list]:
        await update.message.reply_text("❌ Essa categoria já existe! Digite outro nome ou /cancelar.")
        return ADD_CAT_ENTRADA

    cat_list.append(nova_cat)
    update_user_cat_entrada(user_id, cat_list)
    await update.message.reply_text(f"✅ Categoria '{nova_cat}' adicionada com sucesso!")
    await ajuda(update, context)
    return ConversationHandler.END

async def remover_cat_entrada_cmd(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    cat_list = get_user_cat_entrada(user_id)
    msg = (
        "✂️ <b>Digite o nome da categoria de entrada a remover:</b>\n"
        "Suas categorias:\n" + "\n".join(sorted(cat_list))
    )
    await update.message.reply_text(msg, parse_mode="HTML")
    return REMOVE_CAT_ENTRADA

async def process_remove_cat_entrada(update: Update, context: CallbackContext):
    cat_remover = update.message.text.strip()
    user_id = str(update.message.from_user.id)
    cat_list = get_user_cat_entrada(user_id)

    cat_remover_norm = normalize_category(cat_remover)
    cat_list_norm = [normalize_category(c) for c in cat_list]

    if cat_remover_norm not in cat_list_norm:
        await update.message.reply_text(
            "❌ Categoria não encontrada! Digite um nome válido ou /cancelar."
        )
        return REMOVE_CAT_ENTRADA

    # Aqui encontramos a categoria "original" e removemos
    original_cat = None
    for c in cat_list:
        if normalize_category(c) == cat_remover_norm:
            original_cat = c
            break

    if original_cat:
        # prossegue removendo original_cat
        cat_list.remove(original_cat)
        update_user_cat_entrada(user_id, cat_list)
        await update.message.reply_text(f"✅ Categoria '{original_cat}' removida com sucesso!")
        await ajuda(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Erro inesperado ao remover categoria.")
        await ajuda(update, context)
        return ConversationHandler.END

async def confirmar_remove_cat_entrada(update: Update, context: CallbackContext):
    resposta = update.message.text.strip().upper()
    user_id = str(update.message.from_user.id)

    if resposta == "SIM":
        cat_norm = context.user_data.get("remove_cat_entrada")
        if not cat_norm:
            await update.message.reply_text("Ocorreu um erro. Tente novamente.")
            return ConversationHandler.END

        cat_list = get_user_cat_entrada(user_id)
        new_list = [c for c in cat_list if normalize_category(c) != cat_norm]
        update_user_cat_entrada(user_id, new_list)

        await update.message.reply_text(f"✅ Categoria removida com sucesso!")
        
        return ConversationHandler.END
    elif resposta == "NAO":
        await update.message.reply_text("Operação cancelada.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Resposta inválida! Digite SIM ou NAO.")
        return CONFIRM_REMOVE_ENTRADA
    
# --- Menu de Despesas ---
async def despesas_menu(update: Update, context: CallbackContext):
    msg = (
        "📋 <b>Menu de Despesas:</b>\n\n"
        "• /adicionar_despesas - Adicionar uma despesa\n"
        "• /listar_cat_despesas - Listar suas categorias\n"
        "• /adicionar_cat_despesas - Adicionar uma categoria\n"
        "• /remover_cat_despesas - Remover uma categoria\n"
        "• /voltar - Voltar ao menu principal"
    )
    despesas_keyboard = [
        ['/adicionar_despesas', '/listar_cat_despesas'],
        ['/adicionar_cat_despesas', '/remover_cat_despesas'],
        ['/voltar']
    ]
    reply_markup = ReplyKeyboardMarkup(despesas_keyboard, resize_keyboard=True)

    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)

async def listar_categorias(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    cat_list = get_user_categories(user_id)
    msg = "📂 <b>Suas categorias de despesa:</b>\n" + "\n".join(sorted(cat_list))
    await update.message.reply_text(msg, parse_mode="HTML")
    await ajuda(update, context)

# --- Fluxo de Gerenciamento de Categorias ---
(ADD_CAT, REMOVE_CAT, CONFIRM_REMOVE) = range(11, 14)

async def adicionar_categoria_cmd(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    cat_list = get_user_categories(user_id)
    msg = (
        "📥 <b>Digite o nome da categoria a adicionar:</b>\n\n"
        "Suas categorias atuais:\n" + "\n".join(sorted(cat_list))
    )
    await update.message.reply_text(msg, parse_mode="HTML")
    return ADD_CAT

async def process_add_categoria(update: Update, context: CallbackContext):
    nova_cat = update.message.text.strip()
    nova_cat_norm = normalize_category(nova_cat)
    if nova_cat_norm == "GERAL":
        await update.message.reply_text(
            "🚫 <b>A categoria 'GERAL' não pode ser criada!</b>\nEscolha outro nome.",
            parse_mode="HTML"
        )
        return ADD_CAT
    user_id = str(update.message.from_user.id)
    cat_list = get_user_categories(user_id)
    if nova_cat_norm in [normalize_category(c) for c in cat_list]:
        current_list = "\n".join(sorted(cat_list))
        await update.message.reply_text(
            "❌ <b>Essa categoria já existe!</b> Digite outro nome ou /cancelar.\n\n"
            "Suas categorias atuais:\n" + current_list,
            parse_mode="HTML"
        )
        return ADD_CAT
    else:
        cat_list.append(nova_cat_norm)
        update_user_categories(user_id, cat_list)
        updated_list = "\n".join(sorted(cat_list))
        await update.message.reply_text(
            f"✅ <b>Categoria adicionada com sucesso!</b> 🎉\n\nSuas categorias atualizadas:\n{updated_list}",
            parse_mode="HTML"
        )
        await ajuda(update, context)
        return ConversationHandler.END

async def remover_categoria_cmd(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    cat_list = get_user_categories(user_id)
    msg = (
        "✂️ <b>Digite o nome da categoria a remover:</b>\n"
        "Suas categorias:\n" + "\n".join(sorted(cat_list))
    )
    await update.message.reply_text(msg, parse_mode="HTML")
    return REMOVE_CAT

async def process_remove_categoria(update: Update, context: CallbackContext):
    cat_remover = update.message.text.strip()
    if cat_remover.replace(',', '').replace('.', '').isdigit():
        await update.message.reply_text(
            "❌ <b>Entrada inválida!</b> Digite o nome de uma categoria válida ou /cancelar.",
            parse_mode="HTML"
        )
        return REMOVE_CAT
    cat_norm = normalize_category(cat_remover)
    user_id = str(update.message.from_user.id)
    cat_list = get_user_categories(user_id)
    if cat_norm not in [normalize_category(c) for c in cat_list]:
        await update.message.reply_text(
            "❌ <b>Categoria não encontrada!</b> Digite um nome válido ou /cancelar.",
            parse_mode="HTML"
        )
        return REMOVE_CAT
    despesas = carregar_json(DESPESAS_PATH)
    user_expenses = despesas.get(user_id, [])
    count = sum(1 for d in user_expenses if normalize_category(d.get("categoria", "")) == cat_norm)
    if count > 0:
        await update.message.reply_text(
            f"⚠️ <b>A categoria '{cat_norm}' possui {count} despesas cadastradas!</b>\nEssa ação apagará também esses registros.\n\nDigite <b>SIM</b> para confirmar ou <b>NAO</b> para cancelar.",
            parse_mode="HTML"
        )
        context.user_data["remove_category"] = cat_norm
        return CONFIRM_REMOVE
    else:
        new_list = [c for c in cat_list if normalize_category(c) != cat_norm]
        update_user_categories(user_id, new_list)
        await update.message.reply_text(
            f"✅ <b>Categoria '{cat_norm}' removida com sucesso!</b>",
            parse_mode="HTML"
        )
        await update.message.reply_text(
            "Suas categorias atuais:\n" + "\n".join(sorted(new_list)),
            parse_mode="HTML"
        )
        await ajuda(update, context)
        return ConversationHandler.END

async def confirmar_remove_categoria(update: Update, context: CallbackContext):
    resposta = update.message.text.strip().upper()
    user_id = str(update.message.from_user.id)
    if resposta == "SIM":
        cat_norm = context.user_data.get("remove_category")
        if not cat_norm:
            await update.message.reply_text("Ocorreu um erro. Tente novamente.")
            return ConversationHandler.END
        cat_list = get_user_categories(user_id)
        new_list = [c for c in cat_list if normalize_category(c) != cat_norm]
        update_user_categories(user_id, new_list)
        despesas = carregar_json(DESPESAS_PATH)
        if user_id in despesas:
            despesas[user_id] = [d for d in despesas[user_id] if normalize_category(d.get("categoria", "")) != cat_norm]
            salvar_json(DESPESAS_PATH, despesas)
        await update.message.reply_text(
            f"✅ <b>Categoria '{cat_norm}' e suas despesas associadas foram removidas!</b>",
            parse_mode="HTML"
        )
        return ConversationHandler.END
    elif resposta == "NAO":
        await update.message.reply_text(
            "Operação cancelada. Use /ajuda para ver os comandos disponíveis.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "❌ <b>Resposta inválida!</b> Digite <b>SIM</b> para confirmar ou <b>NAO</b> para cancelar.",
            parse_mode="HTML"
        )
        return CONFIRM_REMOVE

# --- Fluxo de Adicionar Despesas ---
async def adicionar_despesas_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Tudo bem! 💸\nVamos lá, qual o valor da despesa?")
    return EXPENSE_VALUE

async def expense_value(update: Update, context: CallbackContext):
    try:
        valor_str = update.message.text.replace(',', '.')
        valor = float(valor_str)
        if valor <= 0:
            await update.message.reply_text("❌ O valor deve ser maior que 0. Tente novamente.")
            return EXPENSE_VALUE
        context.user_data["expense_value"] = valor
        
        # Cria teclado para SIM, NÃO, /cancelar
        keyboard = [
            ["SIM", "NÃO"],
            ["/cancelar"]
        ]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            resize_keyboard=True
        )
        
        await update.message.reply_text(
            "Gostaria de adicionar um comprovante? (SIM/NAO)",
            reply_markup=reply_markup
        )
        return ASK_COMPROVANTE
    except ValueError:
        await update.message.reply_text("⚠️ Informe um valor numérico. Ex: 100 ou 100,50")
        return EXPENSE_VALUE

async def voltar(update: Update, context: CallbackContext):
    await ajuda(update, context)
    return ConversationHandler.END

async def ask_comprovante(update: Update, context: CallbackContext):
    resposta = update.message.text.strip().lower()
    if resposta.replace(',', '').replace('.', '').isdigit():
        await update.message.reply_text("⚠️ Responda apenas SIM ou NAO.")
        return ASK_COMPROVANTE
    if resposta in ["sim", "s"]:
        await update.message.reply_text("📸 Por favor, envie a foto do comprovante.")
        return WAIT_FOR_PHOTO
    else:
        context.user_data["comprovante"] = None
        return await ask_category(update, context)


async def receive_photo(update: Update, context: CallbackContext):
    photo = update.message.photo[-1]
    context.user_data["comprovante"] = photo.file_id
    return await ask_category(update, context)

async def ask_category(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    cat_list = get_user_categories(user_id)

    # Teclado com categorias + '/cancelar'
    opcoes = [[c] for c in sorted(cat_list)]
    opcoes.append(['/cancelar'])  # Caso o usuário desista no meio

    reply_markup = ReplyKeyboardMarkup(
        opcoes,
        one_time_keyboard=True,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "Em qual categoria essa despesa se encaixa? 🗃️\n" +
        "\n".join(sorted(cat_list)) +
        "\n\nPara adicionar uma nova categoria, utilize <b>/adicionar_categoria</b>.",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    return EXPENSE_CATEGORY

async def expense_category(update: Update, context: CallbackContext):
    categoria_input = update.message.text.strip()
    if categoria_input.upper() == "/ADICIONAR_CATEGORIA":
        await update.message.reply_text("Utilize /adicionar_categoria para incluir uma nova categoria.")
        return EXPENSE_CATEGORY
    categoria_normalizada = normalize_category(categoria_input)
    context.user_data["expense_category"] = categoria_normalizada
    user_id = str(update.message.from_user.id)
    cat_list = get_user_categories(user_id)
    if categoria_normalizada not in [normalize_category(c) for c in cat_list]:
        await update.message.reply_text(
            "❌ <b>Categoria não encontrada. Tente novamente.</b>\n\n"
            "Para adicioná-la, use <b>/adicionar_categoria</b> ou <b>/cancelar</b> para parar operação.",
            parse_mode="HTML"
        )
        return EXPENSE_CATEGORY
    await update.message.reply_text(
        "Informe a data da despesa. \n\n❗Exemplo: 01/01/2000",
        reply_markup=ReplyKeyboardRemove()
    )
    return EXPENSE_DATE

async def expense_date(update: Update, context: CallbackContext):
    data_text = update.message.text.strip()
    try:
        data_obj = datetime.strptime(data_text, "%d/%m/%Y")
        if data_obj > datetime.now():
            await update.message.reply_text(
                "⚠️ A data não pode ser futura. \n\n<b>Informe uma data válida (dd/mm/yyyy):</b>",
                parse_mode="HTML"
            )
            return EXPENSE_DATE
        context.user_data["expense_date"] = data_obj.strftime("%d/%m/%Y")
        await update.message.reply_text("Digite uma observação para a despesa ou 'NADA' para pular:")
        return EXPENSE_OBS
    except ValueError:
        await update.message.reply_text(
            "⚠️ Data inválida. \n\n<b>Utilize o formato dd/mm/yyyy:</b>",
            parse_mode="HTML"
        )
        return EXPENSE_DATE

async def expense_obs(update: Update, context: CallbackContext):
    obs = update.message.text.strip()
    if obs.upper() == "NADA":
        obs = ""
    context.user_data["expense_obs"] = obs
    user_id = str(update.message.from_user.id)
    despesas = carregar_json(DESPESAS_PATH)
    user_expenses = despesas.get(user_id, [])
    new_id = max((exp.get("id", 0) for exp in user_expenses), default=0) + 1
    despesa = {
        "id": new_id,
        "valor": context.user_data["expense_value"],
        "categoria": context.user_data["expense_category"],
        "data": context.user_data.get("expense_date"),
        "comprovante": context.user_data.get("comprovante"),
        "observacao": obs
    }
    if user_id not in despesas:
        despesas[user_id] = []
    despesas[user_id].append(despesa)
    salvar_json(DESPESAS_PATH, despesas)
    dados = carregar_json(DADOS_PATH)
    saldo_atual = dados.get(user_id, 0) - context.user_data["expense_value"]
    dados[user_id] = saldo_atual
    salvar_json(DADOS_PATH, dados)
    await update.message.reply_text(
        f"✅ Despesa registrada com sucesso! \n<b>ID: {new_id}\nSeu novo saldo: R$ {saldo_atual:.2f}</b>\n\n"
        "Posso ajudar em mais alguma coisa?\n",
        parse_mode="HTML"
    )
    await ajuda(update, context)
    return ConversationHandler.END

# --- Fluxo de Relatórios ---
async def relatorios_menu(update: Update, context: CallbackContext):
    keyboard = [
        ['/relatorio_entradas', '/relatorio_despesas'],
        ['/cancelar']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        "Escolha o tipo de relatório:\n\n"
        "/relatorio_entradas - Relatório de entradas\n"
        "/relatorio_despesas - Relatório de despesas",
        reply_markup=reply_markup
    )

# ---------------------------
# Fluxo de Relatório de Entradas (sem comprovantes)
# ---------------------------
REPORT_CAT_ENTRADA = 80
REPORT_DATE_START_ENTRADA = 81
REPORT_DATE_END_ENTRADA = 82
# Removemos REPORT_PROV_ENTRADA, pois não queremos exibir comprovantes

async def relatorio_entradas_start(update: Update, context: CallbackContext):
    """Inicia o fluxo de relatório de entradas."""
    user_id = str(update.message.from_user.id)
    cat_list = get_user_cat_entrada(user_id)

    msg = (
        "📊 <b>Relatório de Entradas:</b>\n\n"
        "• Digite o nome de uma categoria ou 'GERAL' para todas.\n\n"
        "Suas categorias de entrada:\n" + "\n".join(cat_list) +
        "\n\nDigite /cancelar para parar a operação."
    )
    keyboard = [[cat] for cat in cat_list]
    keyboard.append(['GERAL'])
    keyboard.append(['/cancelar'])

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
    return REPORT_CAT_ENTRADA

async def report_cat_entrada(update: Update, context: CallbackContext):
    """Recebe a categoria (ou GERAL) e pergunta data inicial."""
    user_id = str(update.message.from_user.id)
    cat_input = update.message.text.strip()
    cat_norm = normalize_category(cat_input)

    cat_list = get_user_cat_entrada(user_id)
    cat_list_norm = [normalize_category(c) for c in cat_list]

    if cat_norm != "GERAL" and cat_norm not in cat_list_norm:
        await update.message.reply_text(
            "❌ Categoria não encontrada! Digite uma categoria existente ou 'GERAL'.\n\n"
            "Suas categorias:\n" + "\n".join(cat_list) +
            "\n\nOu /cancelar para parar.",
            parse_mode="HTML"
        )
        return REPORT_CAT_ENTRADA

    context.user_data["report_cat_entrada"] = cat_norm

    # Teclado data inicial
    keyboard = [
        ["SEM FILTROS"],
        ["/cancelar"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        "📆 Digite a data inicial (dd/mm/yyyy) ou clique em 'SEM FILTROS' para não filtrar.",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return REPORT_DATE_START_ENTRADA

async def report_date_start_entrada(update: Update, context: CallbackContext):
    data_text = update.message.text.strip().upper()
    if data_text == "SEM FILTROS":
        context.user_data["report_date_start_entrada"] = None
        context.user_data["report_date_end_entrada"] = None
        await update.message.reply_text("Gerando relatório sem filtros de data...", parse_mode="HTML")
        return await gerar_relatorio_entradas(update, context)

    try:
        data_obj = datetime.strptime(data_text, "%d/%m/%Y")
        if data_obj > datetime.now():
            await update.message.reply_text("Data não pode ser futura. Tente novamente ou /cancelar.")
            return REPORT_DATE_START_ENTRADA

        context.user_data["report_date_start_entrada"] = data_obj

        keyboard = [
            ["SEM FILTROS"],
            ["/cancelar"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(
            "Digite a data final (dd/mm/yyyy) ou clique em 'SEM FILTROS' para não filtrar:",
            reply_markup=reply_markup
        )
        return REPORT_DATE_END_ENTRADA

    except ValueError:
        await update.message.reply_text("Data inválida! Use dd/mm/yyyy ou /cancelar.")
        return REPORT_DATE_START_ENTRADA

async def report_date_end_entrada(update: Update, context: CallbackContext):
    data_text = update.message.text.strip().upper()
    if data_text == "SEM FILTROS":
        context.user_data["report_date_end_entrada"] = None
        await update.message.reply_text("Gerando relatório...", parse_mode="HTML")
        return await gerar_relatorio_entradas(update, context)

    try:
        data_obj = datetime.strptime(data_text, "%d/%m/%Y")
        if data_obj > datetime.now():
            await update.message.reply_text("Data não pode ser futura. Tente novamente ou /cancelar.")
            return REPORT_DATE_END_ENTRADA

        context.user_data["report_date_end_entrada"] = data_obj
        await update.message.reply_text("Gerando relatório...", parse_mode="HTML")
        return await gerar_relatorio_entradas(update, context)

    except ValueError:
        await update.message.reply_text("Data inválida! Use dd/mm/yyyy ou /cancelar.")
        return REPORT_DATE_END_ENTRADA

async def gerar_relatorio_entradas(update: Update, context: CallbackContext):
    """Relatório de Entradas sem comprovantes."""
    user_id = str(update.message.from_user.id)
    cat_norm = context.user_data["report_cat_entrada"]
    data_inicial = context.user_data.get("report_date_start_entrada")
    data_final = context.user_data.get("report_date_end_entrada")

    entradas = carregar_json(ENTRADAS_PATH)
    user_entradas = entradas.get(user_id, [])

    relatorio = []
    for e in user_entradas:
        try:
            e_data = datetime.strptime(e.get("data", ""), "%d/%m/%Y")
        except ValueError:
            e_data = None

        # Filtro datas
        if data_inicial is not None:
            if e_data is None or e_data < data_inicial:
                continue
        if data_final is not None:
            if e_data is None or e_data > data_final:
                continue

        # Filtro categoria
        e_cat_norm = normalize_category(e.get("categoria", ""))
        if cat_norm == "GERAL" or e_cat_norm == cat_norm:
            relatorio.append(e)

    if not relatorio:
        await update.message.reply_text("Nenhuma entrada encontrada para este período/categoria.")
        return ConversationHandler.END

    msg = "📊 <b>Relatório de Entradas:</b>\n\n"
    for r in relatorio:
        r_id = r.get("id")
        valor = r.get("valor", 0.0)
        cat = r.get("categoria", "")
        data_str = r.get("data", "")
        obs = r.get("observacao", "")
        # comp = r.get("comprovante")  # Se não estiver usando, pode remover

        msg += f"• ID: {r_id}\n"
        msg += f"  Valor: R$ {valor:.2f}\n"
        msg += f"  Categoria: {cat}\n"
        msg += f"  Data: {data_str}\n"
        if obs:
            msg += f"  Obs: {obs}\n"
        msg += "------------------------\n"

    await update.message.reply_text(msg, parse_mode="HTML")
    # Encerramos sem perguntar por comprovantes
    await update.message.reply_text("Relatório finalizado. Use /ajuda para ver os comandos.")
    return ConversationHandler.END

async def relatorios_despesas(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    cat_list = get_user_categories(user_id)

    msg = (
        "📊 <b>Para gerar o relatório:</b>\n"
        "• Digite o nome de uma categoria ou 'GERAL' para todas.\n\n"
        "Suas categorias:\n" + "\n".join(cat_list) +
        "\n\nDigite /cancelar para parar a operação."
    )
    # Teclado com categorias do usuário + 'GERAL' e '/cancelar'
    keyboard = [[cat] for cat in cat_list]
    keyboard.append(['GERAL'])
    keyboard.append(['/cancelar'])

    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
    return REPORT_CATEGORY

async def report_category(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    categoria_input = update.message.text.strip()
    categoria_normalizada = normalize_category(categoria_input)

    available = [normalize_category(c) for c in get_user_categories(user_id)]
    if categoria_normalizada != "GERAL" and categoria_normalizada not in available:
        await update.message.reply_text(
            "❌ <b>Categoria não encontrada!</b> Por favor, digite uma categoria existente ou 'GERAL'.\n\n"
            "Suas categorias:\n" + "\n".join(get_user_categories(user_id)) +
            "\n\nDigite /cancelar para parar a operação.",
            parse_mode="HTML"
        )
        return REPORT_CATEGORY

    context.user_data["report_category"] = categoria_normalizada

    # Teclado para data inicial com SEM FILTROS e /cancelar
    keyboard = [
        ["SEM FILTROS"],
        ["/cancelar"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(
        "📆 Digite a data inicial (dd/mm/yyyy) para o relatório.\n\n"
        "<b>Obs:</b> Se não quiser filtrar por data, clique em 'SEM FILTROS' ou use /cancelar para sair.",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    return REPORT_DATE_START

async def report_date_start(update: Update, context: CallbackContext):
    data_text = update.message.text.strip().upper()
    if data_text == "SEM FILTROS":
        context.user_data["report_date_start"] = None
        context.user_data["report_date_end"] = None
        await update.message.reply_text(
            "Relatório sem filtros de data solicitado. Gerando relatório...",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        return await gerar_relatorio(update, context)

    try:
        data_obj = datetime.strptime(data_text, "%d/%m/%Y")
        if data_obj > datetime.now():
            await update.message.reply_text(
                "⚠️ A data inicial não pode ser futura. Informe uma data válida (dd/mm/yyyy):",
                parse_mode="HTML"
            )
            return REPORT_DATE_START
        context.user_data["report_date_start"] = data_obj

        # Teclado para data final com SEM FILTROS e /cancelar
        keyboard = [
            ["SEM FILTROS"],
            ["/cancelar"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(
            "Agora, informe a data final (dd/mm/yyyy) ou clique em 'SEM FILTROS' para não filtrar:",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return REPORT_DATE_END
    except ValueError:
        await update.message.reply_text(
            "⚠️ Data inválida. Utilize o formato dd/mm/yyyy:",
            parse_mode="HTML"
        )
        return REPORT_DATE_START

async def report_date_end(update: Update, context: CallbackContext):
    data_text = update.message.text.strip().upper()
    if data_text == "SEM FILTROS":
        context.user_data["report_date_end"] = None
        await update.message.reply_text("Gerando relatório...", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return await gerar_relatorio(update, context)

    try:
        data_obj = datetime.strptime(data_text, "%d/%m/%Y")
        if data_obj > datetime.now():
            await update.message.reply_text(
                "⚠️ A data final não pode ser futura. Informe uma data válida (dd/mm/yyyy):",
                parse_mode="HTML"
            )
            return REPORT_DATE_END
        context.user_data["report_date_end"] = data_obj
        await update.message.reply_text("Gerando relatório...", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return await gerar_relatorio(update, context)
    except ValueError:
        await update.message.reply_text(
            "⚠️ Data inválida. Utilize o formato dd/mm/yyyy:",
            parse_mode="HTML"
        )
        return REPORT_DATE_END

async def gerar_relatorio(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    despesas = carregar_json(DESPESAS_PATH)
    lista = despesas.get(user_id, [])
    
    cat_filtro = context.user_data["report_category"]  # Ex: "GERAL" ou "MERCADO"
    data_inicial = context.user_data.get("report_date_start")  # None se SEM FILTROS
    data_final = context.user_data.get("report_date_end")      # None se SEM FILTROS
    
    relatorio = []
    
    for despesa in lista:
        # Tenta converter a data da despesa
        try:
            desp_data = datetime.strptime(despesa.get("data", ""), "%d/%m/%Y")
        except ValueError:
            # Se a data for inválida ou vazia, decide se inclui ou não
            # Exemplo: ignore ou inclua; aqui vou incluir mesmo sem data
            desp_data = None
        
        # 1) Filtro de datas
        if data_inicial is not None:
            if desp_data is None or desp_data < data_inicial:
                continue
        
        if data_final is not None:
            if desp_data is None or desp_data > data_final:
                continue
        
        # 2) Filtro de categoria
        if cat_filtro == "GERAL":
            # Inclui todas as despesas
            relatorio.append(despesa)
        else:
            # Compara categoria normalizada
            if normalize_category(despesa.get("categoria", "")) == cat_filtro:
                relatorio.append(despesa)
    
    # Se não encontrou nenhuma
    if not relatorio:
        await update.message.reply_text(
            "Nenhuma despesa encontrada para o período e categoria informados."
        )
        return ConversationHandler.END
    
    # Caso contrário, exibe o relatório
    msg = "📊 <b>Relatório de Despesas:</b>\n\n"
    ids_comprovantes = []
    
    for d in relatorio:
        desp_id = d.get('id')
        valor = d.get('valor', 0.0)
        categoria = d.get('categoria', '')
        data_desp = d.get('data', '')
        obs = d.get('observacao', '')
        comp = d.get('comprovante')
        
        msg += f"• ID: {desp_id}\n"
        msg += f"  Valor: R$ {valor:.2f}\n"
        msg += f"  Categoria: {categoria}\n"
        msg += f"  Data: {data_desp}\n"
        if obs:
            msg += f"  Obs: {obs}\n"
        comp_str = "Sim" if comp else "Não"
        msg += f"  Comprov: {comp_str}\n"
        msg += "------------------------\n"
        
        if comp:
            ids_comprovantes.append(str(desp_id))
    
    await update.message.reply_text(msg, parse_mode="HTML")
    
    # Salva lista de IDs com comprovante no context.user_data
    context.user_data["ids_comprovantes"] = ids_comprovantes
    
    # Se não tem nenhum comprovante
    if not ids_comprovantes:
        await update.message.reply_text(
            "Nenhuma despesa deste relatório possui comprovante. Digite /cancelar para sair.",
            parse_mode="HTML"
        )
        return ConversationHandler.END
    else:
        # Cria o teclado com os IDs que têm comprovante
        keyboard = [[idc] for idc in ids_comprovantes]
        keyboard.append(['NÃO', '/cancelar'])
        
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await update.message.reply_text(
            "Gostaria de visualizar comprovantes?\n"
            "Selecione o ID abaixo ou digite vários separados por vírgula. Ex: 1,2,3\n"
            "Se não quiser, clique em 'NÃO'.",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return REPORT_PROV

async def report_prov(update: Update, context: CallbackContext):
    resposta = update.message.text.strip().lower()

    # Se o usuário digitar "NÃO" ou "/cancelar", finaliza
    if resposta in ["não", "nao", "/cancelar"]:
        await update.message.reply_text(
            "Relatório finalizado. Use /ajuda para ver os comandos.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    # Senão, processa a lista de IDs
    ids_str = [s.strip() for s in resposta.split(',') if s.strip() != '']
    user_id = str(update.message.from_user.id)
    despesas = carregar_json(DESPESAS_PATH)
    user_expenses = despesas.get(user_id, [])

    # Recupera a lista de IDs de comprovantes ainda disponíveis
    ids_comprovantes = context.user_data.get("ids_comprovantes", [])

    invalid_ids = []
    displayed_any = False

    for id_str in ids_str:
        try:
            expense_id = int(id_str)
        except ValueError:
            invalid_ids.append(id_str)
            continue

        # Verifica se esse ID está na lista de IDs com comprovante
        if str(expense_id) not in ids_comprovantes:
            invalid_ids.append(id_str)
            continue

        # Se está, exibe o comprovante
        found = False
        for d in user_expenses:
            if d.get("id") == expense_id:
                found = True
                comp = d.get("comprovante")
                # Exibe
                await update.message.reply_text(
                    f"Comprovante da despesa ID {expense_id}:",
                    parse_mode="HTML"
                )
                await update.message.reply_photo(photo=comp)
                displayed_any = True

                # Remove esse ID da lista, pois já foi exibido
                if str(expense_id) in ids_comprovantes:
                    ids_comprovantes.remove(str(expense_id))
                break

        if not found:
            invalid_ids.append(id_str)

    # Se teve algum ID inválido ou não encontrado
    if invalid_ids:
        await update.message.reply_text(
            "Não encontrei comprovante(s) para ID(s): " + ", ".join(invalid_ids),
            parse_mode="HTML"
        )

    # Agora verifica se ainda restam IDs
    if ids_comprovantes:
        # Pergunta se deseja ver mais
        keyboard = [[idc] for idc in ids_comprovantes]
        keyboard.append(['NÃO', '/cancelar'])

        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=True
        )

        if displayed_any or invalid_ids:
            await update.message.reply_text(
                "Gostaria de ver mais algum comprovante? Se sim, selecione ou digite o ID. "
                "Caso contrário, clique em 'NÃO'.",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        else:
            # Caso não tenha exibido nenhum, mas ainda tem IDs
            await update.message.reply_text(
                "Selecione o ID abaixo ou digite vários separados por vírgula. Se não quiser, clique em 'NÃO'.",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        return REPORT_PROV
    else:
        # Não restam IDs disponíveis
        await update.message.reply_text(
            "Todos os comprovantes solicitados foram exibidos. Use /ajuda para ver os comandos.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

# --- Cancelar ---
async def cancelar(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Operação cancelada.",
        reply_markup=ReplyKeyboardRemove()
    )
    await ajuda(update, context)
    return ConversationHandler.END

async def voltar(update: Update, context: CallbackContext):
    await ajuda(update, context)
    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()

    # Handlers simples
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))

    # Fluxo para adicionar saldo
    app.add_handler(CommandHandler("entradas", saldo_menu))

    # Handler do menu /relatorios
    app.add_handler(CommandHandler("relatorios", relatorios_menu))


    # Handler para consultar saldo rapidamente
    app.add_handler(CommandHandler("consultar_saldo", consultar_saldo))

    # Conversa de adicionar saldo (com categorias)
    add_saldo_conv = ConversationHandler(
        entry_points=[CommandHandler("adicionar_saldo", adicionar_saldo_start)],
        states={
            ASK_VALOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_valor_saldo)],
            ASK_CAT_ENTRADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_cat_entrada)],
            ASK_OBS_ENTRADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_obs_entrada)],
            ASK_DATA_ENTRADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_data_entrada)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    app.add_handler(add_saldo_conv)

    # Conversa para adicionar/remover categorias de entrada
    cat_entrada_conv = ConversationHandler(
        entry_points=[
            CommandHandler("adicionar_cat_entrada", adicionar_cat_entrada_cmd),
            CommandHandler("remover_cat_entrada", remover_cat_entrada_cmd)
        ],
        states={
            ADD_CAT_ENTRADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_cat_entrada)],
            REMOVE_CAT_ENTRADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_remove_cat_entrada)],
            CONFIRM_REMOVE_ENTRADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_remove_cat_entrada)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    app.add_handler(cat_entrada_conv)

    # Handler para listar categorias de entrada
    app.add_handler(CommandHandler("listar_cat_entrada", listar_cat_entrada))

    app.add_handler(CommandHandler("despesas", despesas_menu))
    app.add_handler(CommandHandler("listar_cat_despesas", listar_categorias))
    app.add_handler(CommandHandler("voltar", voltar))

    # Conversa para fluxo de adicionar despesas
    expense_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("adicionar_despesas", adicionar_despesas_start)],
        states={
            EXPENSE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_value)],
            ASK_COMPROVANTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_comprovante)],
            WAIT_FOR_PHOTO: [MessageHandler(filters.PHOTO, receive_photo)],
            EXPENSE_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_category)],
            EXPENSE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_date)],
            EXPENSE_OBS: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_obs)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    app.add_handler(expense_conv_handler)

    # Conversa para fluxo de relatórios
    report_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("relatorio_despesas", relatorios_despesas)],
        states={
            REPORT_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_category)],
            REPORT_DATE_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_date_start)],
            REPORT_DATE_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_date_end)],
            REPORT_PROV: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_prov)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    app.add_handler(report_conv_handler)

    report_entradas_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("relatorio_entradas", relatorio_entradas_start)],
        states={
            REPORT_CAT_ENTRADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_cat_entrada)],
            REPORT_DATE_START_ENTRADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_date_start_entrada)],
            REPORT_DATE_END_ENTRADA: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_date_end_entrada)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    ) 
    app.add_handler(report_entradas_conv_handler)

    # Conversa para gerenciamento de categorias (adicionar e remover)
    category_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("adicionar_cat_despesas", adicionar_categoria_cmd),
            CommandHandler("remover_cat_despesas", remover_categoria_cmd)
        ],
        states={
            ADD_CAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_categoria)],
            REMOVE_CAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_remove_categoria)],
            CONFIRM_REMOVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_remove_categoria)]
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    app.add_handler(category_conv_handler)

    print("Bot está rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
