import asyncio
from typing import Dict, List
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

BOT_TOKEN = "7003250209:AAFwGlT6bWXt-IRYrnCU4einsHeiN0tPD58"

# Время на ответ (в секундах)
TIME_LIMIT = 10

# Словарь для хранения данных викторины
quiz_data: Dict[int, List[Dict]] = {}

# Файл для хранения рейтинга
RATING_FILE = "rating.txt"

# Создание бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния для конечного автомата
class QuizState(StatesGroup):
    waiting_for_answer = State()

# Функция для загрузки вопросов из файла
def load_questions(filename: str) -> List[Dict]:
    questions = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            question, answer = line.strip().split("|")
            questions.append({"question": question, "answer": answer})
    return questions

# Функция для загрузки рейтинга из файла
def load_rating() -> Dict[int, int]:
    rating = {}
    try:
        with open(RATING_FILE, "r", encoding="utf-8") as f:
            for line in f:
                user_id, score = map(int, line.strip().split(","))
                rating[user_id] = score
    except FileNotFoundError:
        pass
    return rating

# Функция для сохранения рейтинга в файл
def save_rating(rating: Dict[int, int]):
    with open(RATING_FILE, "w", encoding="utf-8") as f:
        for user_id, score in rating.items():
            f.write(f"{user_id},{score}\n")

# Команда /start
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот для викторин. "
        "Чтобы узнать свой id, напишите /id "
        "Напишите /quiz чтобы начать. "
        "(Чтобы посмотреть рейтинг напишите /rating)"
    )

# Создаем словарь для хранения имен пользователей
users_cache = {}

@dp.message_handler(commands=["id"])
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_name = users_cache.get(user_id)

    if not user_name:
        user_name = message.from_user.first_name
        users_cache[user_id] = user_name

    await message.answer(f"Ваш идентификатор: {user_id}")


# Команда /quiz
@dp.message_handler(commands=["quiz"])
async def cmd_quiz(message: types.Message):
    user_id = message.from_user.id

    # Загрузка вопросов
    questions = load_questions("questions.txt")
    quiz_data[user_id] = questions

    # Загрузка рейтинга
    rating = load_rating()

    # Установка начального счета для пользователя
    if user_id not in rating:
        rating[user_id] = 0

    # Сохранение рейтинга
    save_rating(rating)

    # Отправка первого вопроса
    await send_question(user_id)

# Функция для отправки вопроса
async def send_question(user_id: int):
    question_data = quiz_data[user_id][0]
    question_text = question_data["question"]

    await bot.send_message(user_id, question_text)

    await QuizState.waiting_for_answer.set()

    # Запуск таймера
    await asyncio.sleep(TIME_LIMIT)
    await check_answer(user_id, None)

# Проверка ответа
@dp.message_handler(state=QuizState.waiting_for_answer)
async def check_answer(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_answer = message.text if message else None

    question_data = quiz_data[user_id].pop(0)
    correct_answer = question_data["answer"]

    # Загрузка рейтинга
    rating = load_rating()

    if user_answer and user_answer.lower() == correct_answer.lower():
        await message.answer("Правильно!")
        rating[user_id] += 1 # Увеличиваем счет
    else:
        await message.answer(f"Время вышло! Правильный ответ: {correct_answer}")

    # Сохранение рейтинга
    save_rating(rating)

    # Если есть еще вопросы, отправить следующий
    if quiz_data[user_id]:
        await send_question(user_id)
    else:
        await state.finish()
        await show_rating(user_id)

# Команда отображения рейтинга
@dp.message_handler(commands=["rating"])
async def cmd_rating(message: types.Message):
    rating = load_rating()
    if rating:
        sorted_rating = sorted(rating.items(), key=lambda item: item[1], reverse=True)
        rating_text = "\n".join(
            f"{i+1}.{user_id}: {score}" for i, (user_id, score) in enumerate(sorted_rating)
        )
        await message.answer(f"Рейтинг:\n{rating_text}")
    else:
        await message.answer("Рейтинг пока пуст.")

# Показ рейтинга
async def show_rating(user_id: int):
    rating = load_rating()
    await bot.send_message(
        user_id, f"Викторина окончена! Ваш счет: {rating[user_id]}"
    )

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
