import threading
import json
import telebot
import time
import mysql
import re
import requests

import config

from mysql import connector
from telebot import types
from sql import *
from re import search

from flask import Flask, request

APP_API_ADRESS = "http://takecoin.ru/api/"
APP_API_TOKEN = "jOtXnNCoamOkjTTmCDvZ"
TELEGRAM_TOKEN = "6530630106:AAH-gfYhoBCFQvPqsNv4As-PsQnVPSy1XWY"

# создаём приложение Flask
application = Flask(__name__)
flask_started = False

# Создаем экземпляр бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Функция, обрабатывающая команду /start
@bot.message_handler(commands=["start"])
def start(m, res=False):
    user_data = m.from_user
    user_id = m.chat.id

    sql = "SELECT * FROM `users` WHERE `user_id`='"+ str(user_id) +"'"
    result = sql_query(sql)

    if(len(result) == 0):
        sql = "INSERT INTO `users`(`user_id`, `user_app_id`, `status`) VALUES ('" + str(user_id) + "','0','main_menu')"
        sql_query(sql)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Привязка 🖇")
    btn2 = types.KeyboardButton("Ввести код 📄")

    markup.add(btn1, btn2)

    bot.send_message(m.chat.id, "Выберите действие", reply_markup=markup)
   
# Получение сообщений от юзера
@bot.message_handler(content_types=["text"])
def handle_text(message):
    user_data = message.from_user
    user_id = user_data.id

    sql = "SELECT * FROM `users` WHERE `user_id`='" + str(user_id) + "'"
    result = sql_query(sql)

    bot_user_data = result[0]

    if message.text == "Главное меню ⬅️":
        sql = "UPDATE `users` SET `status`='main_menu' WHERE `user_id`='" + str(user_id) + "'"
        sql_query(sql)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Привязка 🖇")
        btn2 = types.KeyboardButton("Ввести код 📄")

        markup.add(btn1, btn2)

        bot.send_message(message.chat.id, "Выберите действие", reply_markup=markup)
        return

    if message.text == "Привязка 🖇":
        bot.send_message(message.chat.id, "Эта функция пока не доступна")
        return

    if message.text == "Ввести код 📄":
        sql = "UPDATE `users` SET `status`='await_code' WHERE `user_id`='" + str(user_id) + "'"
        sql_query(sql)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn = types.KeyboardButton("Главное меню ⬅️")

        markup.add(btn)

        bot.send_message(message.chat.id, "Укажите код", reply_markup=markup)
        return

    if(bot_user_data[2] == "await_code"):
        token = message.text

        data = {
            'telegram_id':user_id,
            'token':token
        }

        headers = {
            'content-type': 'application/json',
            'auth': APP_API_TOKEN
        }

        r = requests.post(APP_API_ADRESS + "service/telegram/veirify", data=json.dumps(data), headers=headers)

        if(r.status_code == 200):
            response = json.loads(r.text)

            if(response['result']['status'] == "account_not_found"):
                markup = types.InlineKeyboardMarkup()

                data = {
                    "action":"signup",
                    "token":token
                }
                
                btn = types.InlineKeyboardButton("Создать аккаунт", callback_data=json.dumps(data))
                markup.add(btn)

                sql = "UPDATE `users` SET `status`='main_menu' WHERE `user_id`='" + str(user_id) + "'"
                sql_query(sql)

                bot.send_message(message.chat.id, "Аккаунт не найден! Вы хотите создать новый?", reply_markup=markup)
                return   

        elif(r.status_code == 404):
            bot.send_message(message.chat.id, "Код не найден!")
            return
        else:
            bot.send_message(message.chat.id, "Ошибка сервера! Попробуйте через 5 минут.")
            return
        

        sql = "UPDATE `users` SET `status`='main_menu' WHERE `user_id`='" + str(user_id) + "'"
        sql_query(sql)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn1 = types.KeyboardButton("Привязка 🖇")
        btn2 = types.KeyboardButton("Ввести код 📄")

        markup.add(btn1, btn2)

        bot.send_message(message.chat.id, "Успешный вход в аккаунт!", reply_markup=markup)
        return

    
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    data = json.loads(call.data)
    user_id = call.message.chat.id

    if(data['action'] == "signup"):
        token = data['token']

        user_data = bot.get_chat(call.message.chat.id)

        data = {
            'telegram_id':user_id,
            'username':(user_data.username, "not_setted")[user_data.username == None],
            'name':(user_data.first_name, "not_setted")[user_data.first_name == None],
            'last_name':(user_data.last_name, "not_setted")[user_data.last_name == None],
            'token':token
        }

        headers = {
            'content-type': 'application/json',
            'auth': APP_API_TOKEN
        }

        r = requests.post(APP_API_ADRESS + "service/telegram/signup", data=json.dumps(data), headers=headers)

        if(r.status_code == 200):
            response = json.loads(r.text)

            app_user_id = response['result']
            sql = "UPDATE `users` SET `user_app_id`='" + str(app_user_id) + "' WHERE `user_id`='"+ str(user_id) +"'"
            sql_query(sql)

            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn1 = types.KeyboardButton("Привязка 🖇")
            btn2 = types.KeyboardButton("Ввести код 📄")

            markup.add(btn1, btn2)
            bot.send_message(call.message.chat.id, "Вы успешно зарегистрировали аккаунт и подтвердили вход!", reply_markup=markup)
            return
        else:
            bot.send_message(call.message.chat.id, "Ошибка при создании аккаунта!")
            return


@application.route('/', methods=['POST'])
def request_worker():
    data = json.loads(request.data)

    print("Worked!")

def app_run():
    while True:
        try:
            application.run(host="0.0.0.0", port=33, ssl_context='adhoc')
        except Exception as ex:
            print(ex)

def bot_polling():
    while True:
        try:
            bot.polling(non_stop=True, interval=0)
        except Exception as e:
            print(e)
            time.sleep(5)
            continue

bot_thread = threading.Thread(target=bot_polling)
bot_thread.daemon = True
bot_thread.start()

# app_thread = threading.Thread(target=app_run)
# app_thread.daemon = True
# app_thread.start()

if __name__ == "__main__":
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break