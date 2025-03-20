from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters
from config import TOKEN
from handlers.basic import start, ajuda, cancelar
from handlers.entradas import (
    saldo_menu, consultar_saldo, adicionar_saldo_start, ask_valor_saldo,
    ask_cat_entrada, ask_obs_entrada, ask_data_entrada, listar_cat_entrada,
    adicionar_cat_entrada_cmd, process_add_cat_entrada, remover_cat_entrada_cmd,
    process_remove_cat_entrada, confirmar_remove_cat_entrada
)
from handlers.despesas import (
    despesas_menu, listar_categorias, adicionar_categoria_cmd, process_add_categoria,
    remover_categoria_cmd, process_remove_categoria, confirmar_remove_categoria,
    adicionar_despesas_start, expense_value, ask_comprovante, receive_photo,
    ask_category, expense_category, expense_date, expense_obs
)
from handlers.reports import (
    relatorios_menu, relatorio_entradas_start, report_cat_entrada, report_date_start_entrada,
    report_date_end_entrada, relatorios_despesas, report_category, report_date_start,
    report_date_end, report_prov
)
import logging

def main():
    app = Application.builder().token(TOKEN).build()

    # Handlers simples
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(CommandHandler("entradas", saldo_menu))
    app.add_handler(CommandHandler("relatorios", relatorios_menu))
    app.add_handler(CommandHandler("consultar_saldo", consultar_saldo))

    # Conversa de adicionar saldo (entradas)
    add_saldo_conv = ConversationHandler(
        entry_points=[CommandHandler("adicionar_saldo", adicionar_saldo_start)],
        states={
            50: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_valor_saldo)],
            51: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_cat_entrada)],
            52: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_obs_entrada)],
            53: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_data_entrada)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    app.add_handler(add_saldo_conv)

    # Conversa para gerenciamento de categorias de entrada
    cat_entrada_conv = ConversationHandler(
        entry_points=[
            CommandHandler("adicionar_cat_entrada", adicionar_cat_entrada_cmd),
            CommandHandler("remover_cat_entrada", remover_cat_entrada_cmd)
        ],
        states={
            60: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_cat_entrada)],
            61: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_remove_cat_entrada)],
            62: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_remove_cat_entrada)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    app.add_handler(cat_entrada_conv)

    app.add_handler(CommandHandler("listar_cat_entrada", listar_cat_entrada))
    app.add_handler(CommandHandler("despesas", despesas_menu))
    app.add_handler(CommandHandler("listar_cat_despesas", listar_categorias))
    app.add_handler(CommandHandler("voltar", lambda update, context: (ajuda(update, context), ConversationHandler.END)))

    # Conversa para fluxo de adicionar despesas
    expense_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("adicionar_despesas", adicionar_despesas_start)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_value)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_comprovante)],
            3: [MessageHandler(filters.PHOTO, receive_photo)],
            4: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_category)],
            5: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_date)],
            6: [MessageHandler(filters.TEXT & ~filters.COMMAND, expense_obs)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    app.add_handler(expense_conv_handler)

    # Conversa para fluxo de relatórios de despesas
    report_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("relatorio_despesas", relatorios_despesas)],
        states={
            7: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_category)],
            8: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_date_start)],
            9: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_date_end)],
            10: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_prov)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    app.add_handler(report_conv_handler)

    # Conversa para fluxo de relatório de entradas
    report_entradas_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("relatorio_entradas", relatorio_entradas_start)],
        states={
            80: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_cat_entrada)],
            81: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_date_start_entrada)],
            82: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_date_end_entrada)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    app.add_handler(report_entradas_conv_handler)

    # Conversa para gerenciamento de categorias de despesas
    category_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("adicionar_cat_despesas", adicionar_categoria_cmd),
            CommandHandler("remover_cat_despesas", remover_categoria_cmd)
        ],
        states={
            11: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_add_categoria)],
            12: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_remove_categoria)],
            13: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_remove_categoria)]
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    app.add_handler(category_conv_handler)

    print("Bot está rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
