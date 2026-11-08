class AppError(Exception):
    """Базовое доменное исключение. Хендлер в app.main переводит его в HTTP-ответ по status_code."""

    status_code: int = 500

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class SecretNotFoundError(AppError):
    """Секрет не найден: не существовал, уже прочитан или истёк TTL."""

    status_code = 404

    def __init__(self) -> None:
        super().__init__("Секрет не найден, уже был прочитан или срок его хранения истёк")


class InvalidTTLError(AppError):
    """TTL вне допустимого диапазона (0 < ttl <= max_ttl_seconds)."""

    status_code = 400

    def __init__(self, max_ttl_seconds: int) -> None:
        super().__init__(f"TTL должен быть в диапазоне от 1 до {max_ttl_seconds} секунд")


class PayloadTooLargeError(AppError):
    """Размер загружаемого файла превышает max_file_size_mb."""

    status_code = 413

    def __init__(self, max_file_size_mb: int) -> None:
        super().__init__(f"Размер файла превышает допустимый лимит {max_file_size_mb} МБ")


class SecretCorruptedError(AppError):
    """Данные в хранилище не удалось расшифровать текущим ключом — повреждение или смена ключа."""

    status_code = 500

    def __init__(self) -> None:
        super().__init__("Не удалось расшифровать секрет: данные повреждены")
