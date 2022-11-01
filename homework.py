import logging
import os
import sys
import time
import requests
import telegram
from exceptions import (ErrorResponse,
                        UnknownStatusHW,
                        CurrentDateError,
                        TelegramError,
                        BadAPIRequest,
                        WrongKeyHomeworks,

                        )

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
    except Exception:
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
        if response.status_code != 200:
            error = (f'Неудовлетворительный статус ответа:'
                     f' {response.status_code},'
                     f' Причина: {response.reason},'
                     f' Текст ответа: {response.text},'
                     f' с параметрами: {params}')
            raise ErrorResponse(error)
        return response.json()
    except Exception as error:
        raise BadAPIRequest(error)


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
        error = f'Homework не является списком {homework}'
        raise TypeError(error)
    logging.debug('Status of homework update')
    if not response.get('current_date'):
        raise CurrentDateError('В словаре отсутствует ключ: "current_date".')
    return homework


def parse_status(homework):
    """Информация о статусе домашней работы."""
    if not isinstance(homework, dict):
        error = f'Homework не является словарем {homework}'
        raise TypeError(error)
    if 'homework_name' not in homework:
        error = f'Ключ homework_name отсутствует {homework}'
        raise KeyError(error)
    if 'status' not in homework:
        error = f'Ключ status отсутствует {homework}'
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
    response = get_api_answer(current_timestamp)
    homeworks = check_response(response)
    previous_error = {}
    current_error = {}
    status_tracking = {}
    while True:
        try:
            if not check_response(response):
                logging.debug('Отсутствуют новые статусы в ответе API.')
                logging.info('Список домашних работ пуст.')
            response = get_api_answer(current_timestamp)
            hw_timestamp = response.get('current_date')
            for homework in homeworks:
                hw_name = homework.get('homework_name')
                hw_status = homework.get('status')
                if hw_name not in status_tracking:
                    status_tracking[hw_name] = hw_status
                    message = parse_status(homework)
                    send_message(bot, message)
                elif status_tracking[hw_name] != hw_status:
                    status_tracking[hw_name] = hw_status
                    message = parse_status(homework)
                    send_message(bot, message)
            current_timestamp = hw_timestamp
        except TelegramError as error:
            message = f'Сбой при отправке сообщения: {error}'
            logging.exception(message)
            logging.error(f'Ошибка при запросе к основному API: {error}')
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
