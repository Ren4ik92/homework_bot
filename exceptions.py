class ErrorResponse(Exception):
    """Error response."""

    pass


class HTTPStatusError(Exception):
    """Пришел статус отличный от 200."""
    pass


class BadAPIRequest(Exception):
    """Неверный запрос API """
    pass


class TelegramError(Exception):
    """Сообщение не отправлено в Telegram."""
    pass


class WrongKeyHomeworks(Exception):
    """Неправильный ключ домашней работы"""
    pass


class UnknownStatusHW(Exception):
    pass


class EmptyValue(Exception):
    pass


class CurrentDateError(Exception):
    pass


class EndpointStatusError(Exception):
    pass
