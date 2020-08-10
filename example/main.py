from example.interfaces import ILogger, ICommunicator, IDatabase


class MainManager(object):
    def __init__(self, logger: ILogger, internal_communicator: ICommunicator, external_communicator: ICommunicator,
                 database: IDatabase):
        self._logger = logger
        self._internal_communicator = internal_communicator
        self._external_communicator = external_communicator
        self._database = database

    def work(self, job_id: str):
        print(f'Working on job {job_id} with {self._logger}, '
              f'{self._internal_communicator}, {self._external_communicator} and {self._database}')


def main(main_manager: MainManager, num_of_jobs: int, job_type: str):
    for job_index in range(num_of_jobs):
        job_id = f'{job_type} #{job_index}'
        main_manager.work(job_id)
