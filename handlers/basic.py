from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler
from utils import carregar_json
from config import DADOS_PATH

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

async def cancelar(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Operação cancelada.",
        reply_markup=ReplyKeyboardRemove()
    )
    await ajuda(update, context)
    return ConversationHandler.END
