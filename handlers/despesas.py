from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler
from datetime import datetime
from utils import carregar_json, salvar_json, normalize_category
from data_manager import get_user_categories, update_user_categories
from config import DESPESAS_PATH, DADOS_PATH, EXPENSE_VALUE, ASK_COMPROVANTE, WAIT_FOR_PHOTO, EXPENSE_CATEGORY, EXPENSE_DATE, EXPENSE_OBS, ADD_CAT, REMOVE_CAT, CONFIRM_REMOVE

async def despesas_menu(update: Update, context: CallbackContext):
    msg = (
        "📋 <b>Menu de Despesas:</b>\n\n"
        "• /adicionar_despesas - Adicionar uma despesa\n"
        "• /listar_cat_despesas - Listar suas categorias\n"
        "• /adicionar_cat_despesas - Adicionar uma categoria\n"
        "• /remover_cat_despesas - Remover uma categoria\n"
        "• /voltar - Voltar ao menu principal"
    )
    keyboard = [
        ['/adicionar_despesas', '/listar_cat_despesas'],
        ['/adicionar_cat_despesas', '/remover_cat_despesas'],
        ['/voltar']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)

async def listar_categorias(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    cat_list = get_user_categories(user_id)
    msg = "📂 <b>Suas categorias de despesa:</b>\n" + "\n".join(sorted(cat_list))
    await update.message.reply_text(msg, parse_mode="HTML")
    from handlers.basic import ajuda
    await ajuda(update, context)

# Gerenciamento de Categorias de Despesas
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
        await update.message.reply_text("🚫 <b>A categoria 'GERAL' não pode ser criada!</b>\nEscolha outro nome.", parse_mode="HTML")
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
        from handlers.basic import ajuda
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
        await update.message.reply_text("❌ <b>Entrada inválida!</b> Digite o nome de uma categoria válida ou /cancelar.", parse_mode="HTML")
        return REMOVE_CAT
    cat_norm = normalize_category(cat_remover)
    user_id = str(update.message.from_user.id)
    cat_list = get_user_categories(user_id)
    if cat_norm not in [normalize_category(c) for c in cat_list]:
        await update.message.reply_text("❌ <b>Categoria não encontrada!</b> Digite um nome válido ou /cancelar.", parse_mode="HTML")
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
        await update.message.reply_text(f"✅ <b>Categoria '{cat_norm}' removida com sucesso!</b>", parse_mode="HTML")
        await update.message.reply_text("Suas categorias atuais:\n" + "\n".join(sorted(new_list)), parse_mode="HTML")
        from handlers.basic import ajuda
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
        await update.message.reply_text(f"✅ <b>Categoria '{cat_norm}' e suas despesas associadas foram removidas!</b>", parse_mode="HTML")
        return ConversationHandler.END
    elif resposta == "NAO":
        await update.message.reply_text("Operação cancelada.", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ <b>Resposta inválida!</b> Digite <b>SIM</b> para confirmar ou <b>NAO</b> para cancelar.", parse_mode="HTML")
        return CONFIRM_REMOVE

# Fluxo para adicionar despesas
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
        keyboard = [["SIM", "NÃO"], ["/cancelar"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Gostaria de adicionar um comprovante? (SIM/NAO)", reply_markup=reply_markup)
        return ASK_COMPROVANTE
    except ValueError:
        await update.message.reply_text("⚠️ Informe um valor numérico. Ex: 100 ou 100,50")
        return EXPENSE_VALUE

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
    opcoes = [[c] for c in sorted(cat_list)]
    opcoes.append(['/cancelar'])
    reply_markup = ReplyKeyboardMarkup(opcoes, one_time_keyboard=True, resize_keyboard=True)
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
        await update.message.reply_text("❌ <b>Categoria não encontrada. Tente novamente.</b>\n\nPara adicioná-la, use <b>/adicionar_categoria</b> ou <b>/cancelar</b> para parar operação.", parse_mode="HTML")
        return EXPENSE_CATEGORY
    await update.message.reply_text("Informe a data da despesa. \n\n❗Exemplo: 01/01/2000", reply_markup=ReplyKeyboardRemove())
    return EXPENSE_DATE

async def expense_date(update: Update, context: CallbackContext):
    data_text = update.message.text.strip()
    try:
        data_obj = datetime.strptime(data_text, "%d/%m/%Y")
        if data_obj > datetime.now():
            await update.message.reply_text("⚠️ A data não pode ser futura. Tente novamente ou /cancelar.", parse_mode="HTML")
            return EXPENSE_DATE
        context.user_data["expense_date"] = data_obj.strftime("%d/%m/%Y")
        await update.message.reply_text("Digite uma observação para a despesa ou 'NADA' para pular:")
        return EXPENSE_OBS
    except ValueError:
        await update.message.reply_text("⚠️ Data inválida. \n\nUtilize o formato dd/mm/yyyy:", parse_mode="HTML")
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
        f"✅ Despesa registrada com sucesso! \n<b>ID: {new_id}\nSeu novo saldo: R$ {saldo_atual:.2f}</b>\n\nPosso ajudar em mais alguma coisa?\n",
        parse_mode="HTML"
    )
    from handlers.basic import ajuda
    await ajuda(update, context)
    return ConversationHandler.END
