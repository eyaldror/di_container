from example.interfaces import ILogger, ICommProtocol, ICommunicator, IDatabase


class FileLogger(ILogger):
    def __init__(self, *, log_path: str) -> None:
        self._log_path = log_path

    def __repr__(self):
        return f"{super().__repr__()[:-1]}'{self._log_path}')"


class UdpCommProtocol(ICommProtocol):
    pass


class HttpCommProtocol(ICommProtocol):
    def __init__(self, logger: ILogger, port: int):
        self.port = port
        super().__init__(logger)

    def __repr__(self):
        return f"{super().__repr__()[:-1]}, {self.port})"


class ExternalCommunicator(ICommunicator):
    pass


class InternalCommunicator(ICommunicator):
    pass


class SqlDatabase(IDatabase):
    pass


class NoSqlDatabase(IDatabase):
    def __init__(self, database_url: str, logger: ILogger):
        super().__init__(database_url, logger)
