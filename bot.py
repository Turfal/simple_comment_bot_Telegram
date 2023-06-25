import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup

import sqlite3

# Token вашего бота
TOKEN = ''

# Инициализация бота
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Имя файла базы данных SQLite
DATABASE_FILE = '3bot.db'

# Создание таблицы 'posts' для хранения постов
def create_posts_table():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            text TEXT,
            media_files TEXT,
            is_published INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# Создание таблицы 'comments' для хранения комментариев
def create_comments_table():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            text TEXT,
            user_id INTEGER,
            username TEXT,
            media_files TEXT
        )
    """)
    conn.commit()
    conn.close()

# Состояния для создания поста и добавления комментария
class NewPost(StatesGroup):
    waiting_for_text = State()
    waiting_for_media = State()
    waiting_for_new_post_text = State()

class NewComment(StatesGroup):
    waiting_for_comment_text = State()

# /start команда
@dp.message_handler(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Добро пожаловать!")

# Функция для проверки, является ли пользователь администратором
def is_admin(user_id):
    # Замените эту логику на свою для определения, является ли пользователь администратором
    return user_id == 554476336

# Функция для создания поста (доступно только администраторам)
@dp.message_handler(Command("create_post"))
async def create_post_command(message: types.Message):
    user_id = message.from_user.id

    if is_admin(user_id):
        await message.answer("Введите текст поста:")
        await NewPost.waiting_for_text.set()
    else:
        await message.answer("У вас нет прав для создания постов.")

# Обработка следующего сообщения с текстом поста
@dp.message_handler(state=NewPost.waiting_for_text)
async def process_create_post_text(message: types.Message, state: FSMContext):
    post_text = message.text.strip()

    async with state.proxy() as data:
        data['post_text'] = post_text

    await message.answer("Отправьте изображение к посту:")
    await NewPost.waiting_for_media.set()

# Обработка следующего сообщения с изображением
@dp.message_handler(content_types=[types.ContentType.PHOTO, types.ContentType.DOCUMENT], state=NewPost.waiting_for_media)
async def process_create_post_media(message: types.Message, state: FSMContext):
    post_text = (await state.get_data()).get('post_text')

    media_files = None
    if message.photo:
        media_files = message.photo[-1].file_id
    elif message.document:
        media_files = message.document.file_id

    async with state.proxy() as data:
        data['media_files'] = media_files

    if media_files:
        await bot.send_chat_action(chat_id=message.chat.id, action=types.ChatActions.UPLOAD_PHOTO)
        await bot.send_photo(chat_id=message.chat.id, photo=media_files, caption=post_text, parse_mode=types.ParseMode.MARKDOWN)

        chat_id = message.chat.id

        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO posts (chat_id, text, media_files) VALUES (?, ?, ?)", (chat_id, post_text, media_files))
        post_id = cursor.lastrowid
        conn.commit()
        conn.close()

        await message.answer(f"Пост успешно создан.\nID поста: {post_id}")
    else:
        await message.answer("Прикрепите изображение к посту.")

    await state.finish()

@dp.message_handler(Command("publish_post"))
async def publish_post(message: types.Message):
    user_id = message.from_user.id

    if is_admin(user_id):
        command_parts = message.text.split()
        if len(command_parts) == 3:
            post_id = command_parts[1]
            topic_id = command_parts[2]
            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
            post = cursor.fetchone()

            if post:
                cursor.execute("UPDATE posts SET is_published = 1 WHERE id = ?", (post_id,))
                conn.commit()

                post_text = post[2]
                # Отправляем текст поста в качестве ответа на сообщение с темой
                await bot.send_message(chat_id=message.chat.id, text=post_text, reply_to_message_id=int(topic_id))
            else:
                await message.answer("Пост не найден.")

            conn.close()
        else:
            await message.answer("Укажите ID поста и ID темы для публикации.")
    else:
        await message.answer("У вас нет прав для публикации постов.")

# Функция для удаления поста (доступно только администраторам)
@dp.message_handler(Command("delete_post"))
async def delete_post(message: types.Message):
    user_id = message.from_user.id

    if is_admin(user_id):
        command_parts = message.text.split()
        if len(command_parts) == 2:
            post_id = command_parts[1]

            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
            post = cursor.fetchone()

            if post:
                cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
                conn.commit()
                conn.close()

                await message.answer(f"Пост с ID {post_id} успешно удален.")
            else:
                await message.answer("Пост не найден.")
        else:
            await message.answer("Укажите ID поста для удаления.")
    else:
        await message.answer("У вас нет прав для удаления постов.")

@dp.message_handler(Command("view_comments"))
async def view_comments(message: types.Message):
    post_id = message.get_args()

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    post = cursor.fetchone()

    if post:
        cursor.execute("SELECT * FROM comments WHERE post_id = ?", (post_id,))
        comments = cursor.fetchall()
        conn.close()

        if comments:
            response = "Комментарии к посту:\n\n"
            for comment in comments:
                response += f"User ID {comment[3]}:\n{comment[2]}\n\n"
            await message.answer(response)
        else:
            await message.answer("К этому посту еще нет комментариев.")
    else:
        await message.answer("Пост не найден.")
        conn.close()

# Функция для просмотра всех постов
@dp.message_handler(Command("view_posts"))
async def view_posts(message: types.Message):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts")
    posts = cursor.fetchall()
    conn.close()

    if posts:
        posts_text = "\n\n".join([f"ID: {post[0]}\n{post[2]}\nСтатус публикации: {'Опубликован' if post[4] == 1 else 'Не опубликован'}" for post in posts])
        await message.answer(f"Список постов:\n\n{posts_text}")
    else:
        await message.answer("Нет доступных постов.")

# Функция для редактирования поста (доступно только администраторам)
@dp.message_handler(Command("edit_post"))
async def edit_post(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if is_admin(user_id):
        command_parts = message.text.split()
        if len(command_parts) == 2:
            post_id = command_parts[1]

            conn = sqlite3.connect(DATABASE_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
            post = cursor.fetchone()

            if post:
                async with state.proxy() as data:
                    data['post_id'] = post_id

                await message.answer(f"Введите новый текст для поста с ID {post_id}.")
                await NewPost.waiting_for_new_post_text.set()
            else:
                await message.answer("Пост не найден.")
        else:
            await message.answer("Укажите ID поста для редактирования.")
    else:
        await message.answer("У вас нет прав для редактирования постов.")

# Обработка следующего сообщения с новым текстом поста
@dp.message_handler(state=NewPost.waiting_for_new_post_text)
async def process_edit_post_text(message: types.Message, state: FSMContext):
    new_post_text = message.text
    post_id = (await state.get_data()).get('post_id')

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE posts SET text = ? WHERE id = ?", (new_post_text, post_id))
    conn.commit()
    conn.close()

    await message.answer(f"Пост с ID {post_id} успешно отредактирован.")
    await state.finish()
    
bot_id = int(TOKEN.split(":")[0])

# Функция для добавления комментария к посту
@dp.message_handler(Command("comment"))
async def add_comment(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id != bot_id:
        args = message.get_args()

        if args:
            split_args = args.split(maxsplit=1)
            if len(split_args) == 2:
                post_id_str, comment_text = split_args
                try:
                    post_id = int(post_id_str)
                    conn = sqlite3.connect(DATABASE_FILE)
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
                    post = cursor.fetchone()

                    if post:
                        cursor.execute("INSERT INTO comments (post_id, text, user_id) VALUES (?, ?, ?)",
                                       (post_id, comment_text, user_id))
                        comment_id = cursor.lastrowid
                        conn.commit()
                        conn.close()

                        await message.answer(f"Комментарий успешно добавлен.\nID комментария: {comment_id}")
                    else:
                        await message.answer("Пост не найден.")
                        conn.close()
                except ValueError:
                    await message.answer("Неверные аргументы команды. Пожалуйста, укажите действительный ID поста.")
            else:
                await message.answer("Неверные аргументы команды. Пожалуйста, укажите ID поста и текст комментария.")
        else:
            await message.answer("Неверная команда. Пожалуйста, укажите ID поста и текст комментария.")

# Регистрация обработчиков команд
dp.register_message_handler(start, commands="start")
dp.register_message_handler(create_post_command, commands="create_post")
dp.register_message_handler(publish_post, commands="publish_post")
dp.register_message_handler(delete_post, commands="delete_post")
dp.register_message_handler(view_posts, commands="view_posts")
dp.register_message_handler(edit_post, commands="edit_post")
dp.register_message_handler(view_comments, commands="view_comments")
dp.register_message_handler(add_comment, commands="comment", state="*")

# Создание таблиц в базе данных
create_posts_table()
create_comments_table()

# Запуск бота
if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
