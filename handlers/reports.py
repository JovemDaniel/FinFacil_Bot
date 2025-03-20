from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler
from datetime import datetime
from utils import carregar_json, salvar_json, normalize_category
from data_manager import get_user_cat_entrada, get_user_categories
from config import ENTRADAS_PATH, REPORT_CAT_ENTRADA, REPORT_DATE_START_ENTRADA, REPORT_DATE_END_ENTRADA, REPORT_CATEGORY, REPORT_DATE_START, REPORT_DATE_END, REPORT_PROV, DESPESAS_PATH

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

# Relatório de Entradas
async def relatorio_entradas_start(update: Update, context: CallbackContext):
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
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(msg, parse_mode="HTML", reply_markup=reply_markup)
    return REPORT_CAT_ENTRADA

async def report_cat_entrada(update: Update, context: CallbackContext):
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
    keyboard = [["SEM FILTROS"], ["/cancelar"]]
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
        keyboard = [["SEM FILTROS"], ["/cancelar"]]
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
        if data_inicial is not None:
            if e_data is None or e_data < data_inicial:
                continue
        if data_final is not None:
            if e_data is None or e_data > data_final:
                continue
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
        msg += f"• ID: {r_id}\n"
        msg += f"  Valor: R$ {valor:.2f}\n"
        msg += f"  Categoria: {cat}\n"
        msg += f"  Data: {data_str}\n"
        if obs:
            msg += f"  Obs: {obs}\n"
        msg += "------------------------\n"
    await update.message.reply_text(msg, parse_mode="HTML")
    await update.message.reply_text("Relatório finalizado. Use /ajuda para ver os comandos.")
    return ConversationHandler.END

# Relatório de Despesas
async def relatorios_despesas(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    cat_list = get_user_categories(user_id)
    msg = (
        "📊 <b>Para gerar o relatório:</b>\n"
        "• Digite o nome de uma categoria ou 'GERAL' para todas.\n\n"
        "Suas categorias:\n" + "\n".join(cat_list) +
        "\n\nDigite /cancelar para parar a operação."
    )
    keyboard = [[cat] for cat in cat_list]
    keyboard.append(['GERAL'])
    keyboard.append(['/cancelar'])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
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
    keyboard = [["SEM FILTROS"], ["/cancelar"]]
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
        await update.message.reply_text("Relatório sem filtros de data solicitado. Gerando relatório...", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return await gerar_relatorio(update, context)
    try:
        data_obj = datetime.strptime(data_text, "%d/%m/%Y")
        if data_obj > datetime.now():
            await update.message.reply_text("⚠️ A data inicial não pode ser futura. Informe uma data válida (dd/mm/yyyy):", parse_mode="HTML")
            return REPORT_DATE_START
        context.user_data["report_date_start"] = data_obj
        keyboard = [["SEM FILTROS"], ["/cancelar"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Agora, informe a data final (dd/mm/yyyy) ou clique em 'SEM FILTROS' para não filtrar:", parse_mode="HTML", reply_markup=reply_markup)
        return REPORT_DATE_END
    except ValueError:
        await update.message.reply_text("⚠️ Data inválida. Utilize o formato dd/mm/yyyy:", parse_mode="HTML")
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
            await update.message.reply_text("⚠️ A data final não pode ser futura. Informe uma data válida (dd/mm/yyyy):", parse_mode="HTML")
            return REPORT_DATE_END
        context.user_data["report_date_end"] = data_obj
        await update.message.reply_text("Gerando relatório...", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return await gerar_relatorio(update, context)
    except ValueError:
        await update.message.reply_text("⚠️ Data inválida. Utilize o formato dd/mm/yyyy:", parse_mode="HTML")
        return REPORT_DATE_END

async def gerar_relatorio(update: Update, context: CallbackContext):
    user_id = str(update.message.from_user.id)
    despesas = carregar_json(DESPESAS_PATH)
    lista = despesas.get(user_id, [])
    cat_filtro = context.user_data["report_category"]
    data_inicial = context.user_data.get("report_date_start")
    data_final = context.user_data.get("report_date_end")
    relatorio = []
    for despesa in lista:
        try:
            desp_data = datetime.strptime(despesa.get("data", ""), "%d/%m/%Y")
        except ValueError:
            desp_data = None
        if data_inicial is not None:
            if desp_data is None or desp_data < data_inicial:
                continue
        if data_final is not None:
            if desp_data is None or desp_data > data_final:
                continue
        if cat_filtro == "GERAL":
            relatorio.append(despesa)
        else:
            if normalize_category(despesa.get("categoria", "")) == cat_filtro:
                relatorio.append(despesa)
    if not relatorio:
        await update.message.reply_text("Nenhuma despesa encontrada para o período e categoria informados.")
        return ConversationHandler.END
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
    context.user_data["ids_comprovantes"] = ids_comprovantes
    if not ids_comprovantes:
        await update.message.reply_text("Nenhuma despesa deste relatório possui comprovante. Digite /cancelar para sair.", parse_mode="HTML")
        return ConversationHandler.END
    else:
        keyboard = [[idc] for idc in ids_comprovantes]
        keyboard.append(['NÃO', '/cancelar'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "Gostaria de visualizar comprovantes?\nSelecione o ID abaixo ou digite vários separados por vírgula. Ex: 1,2,3\nSe não quiser, clique em 'NÃO'.",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return REPORT_PROV

async def report_prov(update: Update, context: CallbackContext):
    resposta = update.message.text.strip().lower()
    if resposta in ["não", "nao", "/cancelar"]:
        await update.message.reply_text("Relatório finalizado. Use /ajuda para ver os comandos.", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    ids_str = [s.strip() for s in resposta.split(',') if s.strip() != '']
    user_id = str(update.message.from_user.id)
    despesas = carregar_json(DESPESAS_PATH)
    user_expenses = despesas.get(user_id, [])
    ids_comprovantes = context.user_data.get("ids_comprovantes", [])
    invalid_ids = []
    displayed_any = False
    for id_str in ids_str:
        try:
            expense_id = int(id_str)
        except ValueError:
            invalid_ids.append(id_str)
            continue
        if str(expense_id) not in ids_comprovantes:
            invalid_ids.append(id_str)
            continue
        found = False
        for d in user_expenses:
            if d.get("id") == expense_id:
                found = True
                comp = d.get("comprovante")
                await update.message.reply_text(f"Comprovante da despesa ID {expense_id}:", parse_mode="HTML")
                await update.message.reply_photo(photo=comp)
                displayed_any = True
                if str(expense_id) in ids_comprovantes:
                    ids_comprovantes.remove(str(expense_id))
                break
        if not found:
            invalid_ids.append(id_str)
    if invalid_ids:
        await update.message.reply_text("Não encontrei comprovante(s) para ID(s): " + ", ".join(invalid_ids), parse_mode="HTML")
    if ids_comprovantes:
        keyboard = [[idc] for idc in ids_comprovantes]
        keyboard.append(['NÃO', '/cancelar'])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        if displayed_any or invalid_ids:
            await update.message.reply_text("Gostaria de ver mais algum comprovante? Se sim, selecione ou digite o ID. Caso contrário, clique em 'NÃO'.", parse_mode="HTML", reply_markup=reply_markup)
        else:
            await update.message.reply_text("Selecione o ID abaixo ou digite vários separados por vírgula. Se não quiser, clique em 'NÃO'.", parse_mode="HTML", reply_markup=reply_markup)
        return REPORT_PROV
    else:
        await update.message.reply_text("Todos os comprovantes solicitados foram exibidos. Use /ajuda para ver os comandos.", parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
