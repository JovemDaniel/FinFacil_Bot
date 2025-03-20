from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler
from datetime import datetime
from utils import carregar_json, salvar_json, normalize_category
from data_manager import get_user_cat_entrada, update_user_cat_entrada
from config import DADOS_PATH, ASK_VALOR, ASK_CAT_ENTRADA, ASK_OBS_ENTRADA, ASK_DATA_ENTRADA, ADD_CAT_ENTRADA, REMOVE_CAT_ENTRADA, CONFIRM_REMOVE_ENTRADA, ENTRADAS_PATH

async def saldo_menu(update: Update, context: CallbackContext):
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
    dados = carregar_json(DADOS_PATH)
    user_id = str(update.message.from_user.id)
    saldo_usuario = dados.get(user_id, 0)
    await update.message.reply_text(f"💰 Seu saldo atual é: R$ {saldo_usuario:.2f}")

# Fluxo para adicionar saldo (entrada)
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
    user_id = str(update.message.from_user.id)
    cat_list = get_user_cat_entrada(user_id)
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
    cat_escolhida_norm = normalize_category(cat_escolhida)
    cat_list_norm = [normalize_category(c) for c in cat_list]
    if cat_escolhida_norm not in cat_list_norm:
        await update.message.reply_text("Categoria inválida! Tente novamente ou /cancelar.")
        return ASK_CAT_ENTRADA
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
        await update.message.reply_text("Data inválida! Use o formato dd/mm/yyyy ou /cancelar.")
        return ASK_DATA_ENTRADA
    if data_obj > datetime.now():
        await update.message.reply_text("⚠️ A data não pode ser futura. Informe uma data válida (dd/mm/yyyy):", parse_mode="HTML")
        return ASK_DATA_ENTRADA
    context.user_data["data_entrada"] = data_obj.strftime("%d/%m/%Y")
    user_id = str(update.message.from_user.id)
    dados = carregar_json(DADOS_PATH)
    saldo_atual = dados.get(user_id, 0)
    valor = context.user_data["valor_entrada"]
    novo_saldo = saldo_atual + valor
    dados[user_id] = novo_saldo
    salvar_json(DADOS_PATH, dados)
    entradas = carregar_json(ENTRADAS_PATH)
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
    salvar_json(ENTRADAS_PATH, entradas)
    msg = (
        f"✅ Entrada registrada!\n"
        f"Valor: R$ {valor:.2f}\n"
        f"Categoria: {context.user_data['cat_entrada']}\n"
        f"Data: {context.user_data['data_entrada']}\n"
        f"Obs: {context.user_data['obs_entrada']}\n\n"
        f"💰 Novo saldo: R$ {novo_saldo:.2f}"
    )
    await update.message.reply_text(msg)
    from handlers.basic import ajuda
    await ajuda(update, context)
    return ConversationHandler.END

# Gerenciamento de categorias de entrada
async def listar_cat_entrada(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    cat_list = get_user_cat_entrada(user_id)
    msg = "📂 <b>Suas categorias de entrada:</b>\n" + "\n".join(sorted(cat_list))
    await update.message.reply_text(msg, parse_mode="HTML")
    from handlers.basic import ajuda
    await ajuda(update, context)

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
    from handlers.basic import ajuda
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
        await update.message.reply_text("❌ Categoria não encontrada! Digite um nome válido ou /cancelar.")
        return REMOVE_CAT_ENTRADA
    original_cat = None
    for c in cat_list:
        if normalize_category(c) == cat_remover_norm:
            original_cat = c
            break
    if original_cat:
        cat_list.remove(original_cat)
        update_user_cat_entrada(user_id, cat_list)
        await update.message.reply_text(f"✅ Categoria '{original_cat}' removida com sucesso!")
        from handlers.basic import ajuda
        await ajuda(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Erro inesperado ao remover categoria.")
        from handlers.basic import ajuda
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
