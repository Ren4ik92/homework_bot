import logging
import os
import sys
import time
import requests
import telegram
from exceptions import *

from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Отправляем сообщение')
    except TelegramError:
        raise TelegramError(f'Сбои при отправке сообщения в Telegram: '
                            f'{message}')
    else:
        logging.info(f'Сообщение успешно отправлено: {message}')


def get_api_answer(current_timestamp):
    """Выполнение запроса к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        logging.info(f'Отправляем запрос к API. endpoint: {ENDPOINT},'
                     f'headers: {HEADERS}, params: {params}')
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise BadAPIRequest(error)
    if response.status_code != 200:
        error = f'Неудовлетворительный статус ответа: {response.status_code}'
        raise ErrorResponse(error)
    return response.json()


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        error = f'Response не является словарем {response}'
        raise TypeError(error)
    if 'homeworks' not in response:
        error = f'Ключа homeworks в ответе нет: {response}'
        raise WrongKeyHomeworks(error)
    homework = response['homeworks']
    if not isinstance(homework, list):
        error = 'Homework не является списком'
        raise TypeError(error)
    if not homework:
        error = f'Список {homework[0]} пуст'
        raise EmptyValue(error)
    logging.debug('Status of homework update')
    if not response.get('current_date'):
        raise CurrentDateError('В словаре отсутствует ключ: "current_date".')
    return homework


def parse_status(homework):
    """Информация о статусе домашней работы."""
    if not isinstance(homework, dict):
        error = 'Homework не является словарем'
        raise TypeError(error)
    if 'homework_name' not in homework:
        error = 'Ключ homework_name отсутствует'
        raise KeyError(error)
    if 'status' not in homework:
        error = 'Ключ status отсутствует'
        raise KeyError(error)
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        error = f'Неизвестный статус: {homework_status}'
        raise UnknownStatusHW(error)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    if not PRACTICUM_TOKEN:
        logging.critical(
            "Отсутствует обязательная переменная окружения:"
            "'PRACTICUM_TOKEN' Программа принудительно остановлена.")
        return False
    if not TELEGRAM_TOKEN:
        logging.critical(
            "Отсутствует обязательная переменная окружения:"
            "'TELEGRAM_TOKEN' Программа принудительно остановлена.")
        return False
    if not TELEGRAM_CHAT_ID:
        logging.critical(
            "Отсутствует обязательная переменная окружения:"
            "'TELEGRAM_CHAT_ID' Программа принудительно остановлена.")
        return False
    return True


def main():
    """Основная функция."""
    if not check_tokens():
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time() - 30 * 24 * 60 * 60)
    status = ''
    previous_error = {}
    current_error = {}
    while True:
        try:
            response = get_api_answer(current_timestamp)
            hw_timestamp = response.get('current_date')
            if not check_response(response):
                logging.debug('Отсутствуют новые статусы в ответе API.')
                logging.info('Список домашних работ пуст.')
            else:
                homeworks = check_response(response)
                homework = homeworks[0]
                homework_verdict = parse_status(homework)
                send_message(bot, homework_verdict)
            current_timestamp = hw_timestamp
        except telegram.TelegramError as error:
            message = f'Сбой при отправке сообщения: {error}'
            logging.exception(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.exception(message)
            current_error['message'] = message
            if previous_error != current_error:
                send_message(bot, message)
                previous_error = current_error.copy()
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        level=logging.INFO
    )
    main()
