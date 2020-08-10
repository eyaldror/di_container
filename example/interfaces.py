from abc import ABC


class ILogger(ABC):
    def __repr__(self):
        return f'{self.__class__.__name__}()'


class ICommProtocol(ABC):
    def __init__(self, logger: ILogger):
        self._logger = logger

    def __repr__(self):
        return f'{self.__class__.__name__}({self._logger})'


class ICommunicator(ABC):
    def __init__(self, comm_protocol: ICommProtocol, logger: ILogger):
        self._comm_protocol = comm_protocol
        self._logger = logger

    def __repr__(self):
        return f'{self.__class__.__name__}({self._comm_protocol}, {self._logger})'


class IDatabase(ABC):
    def __init__(self, database_url: str, logger: ILogger):
        self._database_url = database_url
        self._logger = logger

    def __repr__(self):
        return f'{self.__class__.__name__}({self._database_url}, {self._logger})'
