# 💸 FinFácil Bot - Telegram

Um bot de controle financeiro pessoal para Telegram desenvolvido em Python. Com ele, você pode registrar entradas de valores, categorias, observações e datas, mantendo seu saldo sempre atualizado. Ideal para quem quer um controle simples e eficiente diretamente pelo Telegram!

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Funcionalidades

- ✅ Registro de entradas financeiras
  - Valor personalizado
  - Categoria (definida pelo usuário)
  - Observação opcional
  - Data personalizada (impede datas futuras)
- 📊 Consulta de relatórios de entradas por categoria e período
- 💰 Controle automático do saldo do usuário
- 🚫 Comando `/cancelar` para interromper operações a qualquer momento
- 📂 Armazenamento dos dados localmente em arquivos JSON
- 🔒 Persistência individualizada por usuário (por ID do Telegram)
  
---

## 🚀 Como rodar o projeto

### Pré-requisitos

- Python 3.10 ou superior
- Token do BotFather (crie um bot no Telegram)

### Instalação

1. Clone este repositório:

```bash
git clone https://github.com/JovemDaniel/FinFacil_Bot.git
cd FinFacil_Bot
python bot.py
