import os
import logging
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import asyncio
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

BOT_TOKEN=os.getenv('BOT_TOKEN')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словарь для хранения адресов кошельков пользователей
user_wallets = {}

# Функция для записи диалога в лог-файл пользователя
def log_user_message(user_id, message):
    with open(f'{user_id}.log', 'a') as f:
        f.write(f'{datetime.now()}: {message}\n')  # Добавление времени к записи

# Команда /start
@dp.message(Command('start'))
async def start(message: Message):
    user_id = message.from_user.id
    log_user_message(user_id, f"User started bot. Message: {message.text}")
    await message.answer("Привет! Я бот для отслеживания транзакций. Введите /help для списка команд.")

# Команда /help
@dp.message(Command('help'))
async def help_command(message: Message):
    user_id = message.from_user.id
    log_user_message(user_id, f"Help requested. Message: {message.text}")
    await message.answer(
        "/start - Запустить бота\n"
        "/set_wallet - Указать Ethereum-кошелек для отслеживания\n"
        "/check_transactions - Проверить транзакции по кошельку\n"
        "/balance - Узнать баланс на кошельке"
    )

# Команда /set_wallet
@dp.message(Command('set_wallet'))
async def set_wallet(message: Message):
    user_id = message.from_user.id
    log_user_message(user_id, f"Wallet set requested. Message: {message.text}")
    await message.answer("Введите адрес вашего Ethereum-кошелька:")

    # Ожидание ответа с кошельком
    @dp.message()
    async def receive_wallet(wallet_message: Message):
        wallet_address = wallet_message.text.strip()
        user_wallets[user_id] = wallet_address  # Сохраняем кошелек в словаре
        log_user_message(user_id, f"Wallet address set to: {wallet_address}")
        await wallet_message.answer(f"Кошелек {wallet_address} установлен для отслеживания.")

    dp.message.register(receive_wallet)

# Функция для получения транзакций
async def get_transactions(wallet_address):
    url = f'https://api.etherscan.io/api?module=account&action=txlist&address={wallet_address}&startblock=0&endblock=99999999&page=1&offset=10&sort=asc&apikey={ETHERSCAN_API_KEY}'
    response = requests.get(url)
    return response.json()

# Команда /check_transactions
@dp.message(Command('check_transactions'))
async def check_transactions(message: Message):
    user_id = message.from_user.id
    log_user_message(user_id, f"Transactions check requested. Message: {message.text}")
    
    wallet_address = user_wallets.get(user_id)  # Получаем кошелек из словаря
    
    if not wallet_address:
        await message.answer("Вы не указали адрес кошелька. Используйте команду /set_wallet.")
        return
    
    transactions = await get_transactions(wallet_address)
    
    if transactions['status'] == '1':
        log_user_message(user_id, "Transactions fetched successfully.")
        transactions_list = transactions['result'][:5]  # Получаем первые 5 транзакций
        for transaction in transactions_list:
            transaction_text = json.dumps(transaction, indent=4)  # Преобразуем словарь в строку
            await message.answer(transaction_text)  # Отправляем каждую транзакцию отдельно
    else:
        await message.answer("Не удалось получить транзакции. Проверьте правильность введенного адреса кошелька.")

# Функция для получения баланса
async def get_balance(wallet_address):
    url = f'https://api.etherscan.io/api?module=account&action=balance&address={wallet_address}&tag=latest&apikey={ETHERSCAN_API_KEY}'
    response = requests.get(url)
    return response.json()

# Команда /balance
@dp.message(Command('balance'))
async def balance_command(message: Message):
    user_id = message.from_user.id
    log_user_message(user_id, f"Balance check requested. Message: {message.text}")
    
    wallet_address = user_wallets.get(user_id)  # Получаем кошелек из словаря
    
    if not wallet_address:
        await message.answer("Вы не указали адрес кошелька. Используйте команду /set_wallet.")
        return
    
    data = await get_balance(wallet_address)

    if data['status'] == '1':
        balance = int(data['result']) / 10**18  # Преобразуем баланс в ETH
        log_user_message(user_id, f"Balance fetched: {balance} ETH.")
        await message.answer(f"Баланс кошелька: {balance} ETH")
    else:
        await message.answer("Не удалось получить баланс. Проверьте правильность введенного адреса.")

# Основная функция запуска бота
async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

# Запуск бота
if __name__ == '__main__':
    asyncio.run(main())