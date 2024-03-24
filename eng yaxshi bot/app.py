import telebot
from telebot import types
from datetime import datetime, timedelta
import json
from config import TOKEN, CHANNEL_ID, admin_ids

bot = telebot.TeleBot(TOKEN)

# Инициализация данных для голосования
votes = {}
vote_start_date = datetime.now()
vote_duration = timedelta(weeks=2)
vote_end_date = vote_start_date + vote_duration
options = []  # Инициализация опций для голосования

# Словарь состояний администраторов
admin_states = {}


def is_admin(user_id):
    return user_id in admin_ids

# Обновление функций сохранения и загрузки голосов для включения опций
def save_votes():
    with open('votes.json', 'w') as file:
        json.dump({'votes': votes, 'options': options, 'start_date': vote_start_date.timestamp()}, file)

def load_votes():
    global vote_start_date, vote_end_date, options
    try:
        with open('votes.json', 'r') as file:
            data = json.load(file)
            vote_start_date = datetime.fromtimestamp(data['start_date'])
            vote_end_date = vote_start_date + vote_duration
            options = data.get('options', options)
            return data['votes']
    except FileNotFoundError:
        return {}

votes = load_votes()

def check_vote_time():
    return datetime.now() < vote_end_date

# Добавьте обработчики и остальной код здесь

def check_subscription_status(channel_id, user_id):
    try:
        chat_member = bot.get_chat_member(channel_id, user_id)
        return chat_member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        print(f"Ошибка при проверке подписки: {e}")
        return False

def start_markup():
    markup = types.InlineKeyboardMarkup(row_width=1)
    subscribe_button = types.InlineKeyboardButton(text="Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_ID[1:]}")
    check_subscription_button = types.InlineKeyboardButton(text="Obunani tekshirish", callback_data="check_subscription")
    markup.add(subscribe_button, check_subscription_button)
    return markup

def voting_markup():
    markup = types.InlineKeyboardMarkup()
    for option in options:
        markup.add(types.InlineKeyboardButton(option, callback_data=f"vote_{options.index(option)}"))
    return markup


@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()[1:]  # Получаем аргументы команды

    user_id = message.from_user.id
    if is_admin(user_id):
        # Администратору предлагаем админ-панель
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        buttons = [
            types.KeyboardButton('Начать голосование'),
            types.KeyboardButton('Закончить голосование'),
            types.KeyboardButton('Добавить опцию'),
            types.KeyboardButton('Удалить опцию')
        ]
        markup.add(*buttons)
        bot.send_message(message.chat.id, "Добро пожаловать в админ-панель.", reply_markup=markup)
    else:
        # Обычному пользователю предлагаем подписаться на канал
        markup = start_markup()  # Используем ранее определенную функцию для создания клавиатуры
        bot.send_message(message.chat.id, "Ovoz berish uchun kanalga obuna bo'ling.", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_subscription(call):
    if check_subscription_status(CHANNEL_ID, call.from_user.id):
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text="Endi ovoz berishingiz mumkin:", reply_markup=voting_markup())
    else:
        bot.answer_callback_query(call.id, "Iltimos, ovoz berish uchun kanalga obuna bo'ling.", show_alert=True)


def update_channel_message():
    # Создаем новую inline-клавиатуру с обновленным количеством голосов
    markup = types.InlineKeyboardMarkup()
    for option in options:
        votes_count = len(votes.get(option, []))  # Получаем текущее количество голосов для варианта
        button_text = f"{option} - {votes_count} "  # Формируем текст кнопки
        markup.add(types.InlineKeyboardButton(button_text, url=f"https://t.me/engyaxshiuz_bot"))


    try:
        bot.edit_message_caption(caption=chennel_vote_text, chat_id=CHANNEL_ID,
                              message_id=channel_vote_message_id, reply_markup=markup)
    except Exception as e:
        print(f"Ошибка при обновлении сообщения в канале: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("vote_"))
def handle_vote(call):
    if not check_vote_time():
        bot.answer_callback_query(call.id, "Ovoz berish tugadi.", show_alert=True)
        return

    option_index = int(call.data.split("_")[1])
    option = options[option_index]
    user_id = call.from_user.id

    # Проверяем, голосовал ли пользователь уже
    if any(user_id in v for v in votes.values()):
        bot.answer_callback_query(call.id, "Siz ovoz bergansiz!", show_alert=True)
        return

    if option in votes:
        votes[option].append(user_id)
    else:
        votes[option] = [user_id]
    save_votes()
    bot.answer_callback_query(call.id, "Ovozingiz uchun rahmat!")
    update_channel_message()


# Добавление и удаление опций голосования реализованы ранее

@bot.message_handler(func=lambda message: message.text in ['Начать голосование', 'Закончить голосование', 'Публикация результатов'] and is_admin(message.from_user.id))
def admin_actions(message):
    if message.text == 'Начать голосование':
        start_vote(message)
    elif message.text == 'Закончить голосование':
        end_vote(message)
    elif message.text == 'Публикация результатов':
        publish_results_command(message)

@bot.message_handler(func=lambda message: message.text == 'Добавить опцию' and is_admin(message.from_user.id))
def prompt_for_option_to_add(message):
    admin_states[message.from_user.id] = 'adding_option'
    bot.send_message(message.chat.id, "Введите название опции, которую вы хотите добавить:")

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'adding_option')
def add_option(message):
    option = message.text
    if option in options:
        bot.send_message(message.chat.id, "Эта опция уже существует.")
    else:
        options.append(option)
        save_votes()
        bot.send_message(message.chat.id, f"Опция '{option}' успешно добавлена.")
    admin_states[message.from_user.id] = None  # Сброс состояния администратора

@bot.message_handler(func=lambda message: message.text == 'Удалить опцию' and is_admin(message.from_user.id))
def prompt_for_option_to_remove(message):
    admin_states[message.from_user.id] = 'removing_option'
    bot.send_message(message.chat.id, "Введите название опции, которую вы хотите удалить:")

@bot.message_handler(func=lambda message: admin_states.get(message.from_user.id) == 'removing_option')
def remove_option(message):
    option = message.text
    if option not in options:
        bot.send_message(message.chat.id, "Такой опции не существует.")
    else:
        options.remove(option)
        save_votes()
        bot.send_message(message.chat.id, f"Опция '{option}' успешно удалена.")
    admin_states[message.from_user.id] = None  # Сброс состояния администратора

# Функции админ-панели
@bot.message_handler(commands=['start_vote'])
def start_vote(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "У вас нет прав использовать эту команду.")
        return
    admin_states[message.from_user.id] = 'awaiting_vote_photo'
    bot.reply_to(message, "Пожалуйста, отправьте фотографию для начала голосования.")
    global vote_start_date, vote_end_date, votes
    vote_start_date = datetime.now()
    vote_end_date = vote_start_date + vote_duration
    votes = {}  # Обнуляем текущие голоса
    save_votes()

@bot.message_handler(commands=['end_vote'])
def end_vote(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "У вас нет прав использовать эту команду.")
        return
    global vote_end_date
    vote_end_date = datetime.now()  # Установка времени окончания голосования на текущий момент
    save_votes()
    bot.reply_to(message, "Голосование завершено.")

@bot.message_handler(commands=['publish_results'])
def publish_results_command(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "У вас нет прав на публикацию результатов голосования.")
        return
    results_text = format_results()
    bot.send_message(CHANNEL_ID, results_text)

def format_results():
    results = "Результаты голосования:\n"
    total_votes = sum(len(v) for v in votes.values())
    for i, option in enumerate(options, start=1):
        votes_count = len(votes.get(f"vote_{i}", []))
        percentage = (votes_count / total_votes * 100) if total_votes else 0
        results += f"{option}: {votes_count} голос(ов) ({percentage:.2f}%)\n"
    return results if total_votes else "Голосование ещё не началось или никто не проголосовал."


# Функция для создания инлайн клавиатуры с кнопкой запроса результатов
def results_request_markup():
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton("Посмотреть результаты", callback_data="request_results")
    markup.add(button)
    return markup

# Обработчик CallbackQuery для обновления результатов
@bot.callback_query_handler(func=lambda call: call.data == "request_results")
def request_results(call):
    if check_vote_time():
        # Формируем текст результатов голосования
        results_text = format_results()
        # Обновляем сообщение с результатами
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=results_text, reply_markup=results_request_markup())
    else:
        bot.answer_callback_query(call.id, "Голосование не активно в данный момент.", show_alert=True)



@bot.message_handler(content_types=['photo'], func=lambda message: admin_states.get(message.from_user.id) == 'awaiting_vote_photo')
def receive_vote_photo(message):
    admin_states[message.from_user.id] = {'awaiting_vote_text': message.photo[-1].file_id}  # Сохраняем ID фотографии
    bot.reply_to(message, "Теперь введите текст для поста голосования.")

@bot.message_handler(func=lambda message: isinstance(admin_states.get(message.from_user.id), dict) and 'awaiting_vote_text' in admin_states[message.from_user.id])
def post_vote_with_photo_and_text(message):
    photo_id = admin_states[message.from_user.id]['awaiting_vote_text']
    text = message.text + "\n\nВыберите вариант для голосования:"
    markup = types.InlineKeyboardMarkup()
    # Добавляем кнопки для каждого варианта голосования с начальным количеством голосов 0
    for index, option in enumerate(options):
        markup.add(types.InlineKeyboardButton(f"{option} - 0", url=f"https://t.me/{bot.get_me().username}"))  # Функция, создающая инлайн клавиатуру для голосования, остаётся без изменений

    # Отправляем сообщение в канал с inline-клавиатурой
    msg = bot.send_photo(CHANNEL_ID, photo=photo_id, caption=text, reply_markup=markup)
    global channel_vote_message_id, chennel_vote_text
    channel_vote_message_id = msg.message_id
    chennel_vote_text = message.text
    save_votes()
    bot.reply_to(message, "Голосование началось.")

bot.polling(non_stop=True)
