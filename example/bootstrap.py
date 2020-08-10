from di_container.container import Container, Instantiation

from example.interfaces import IDatabase, ILogger, ICommunicator, ICommProtocol
from example.implementations import UdpCommProtocol, HttpCommProtocol, \
    InternalCommunicator, ExternalCommunicator, \
    SqlDatabase, NoSqlDatabase, \
    FileLogger
from example.main import MainManager, main
import example.config

if __name__ == '__main__':
    app_config = example.config.load_config('c:/example/config.json')

    base_container = Container('base')
    # register config values
    base_container.register_value(app_config['network']['http_port']).to_name('port', int)
    base_container.register_value(app_config['logging']['log_path']).to_name('log_path', str)
    base_container.register_value(app_config['database']['database_url']).to_name('database_url', str)
    # register core classes
    base_container.register_type(FileLogger).to_type(ILogger)
    base_container.register_type(NoSqlDatabase).to_type(IDatabase)
    base_container.register_type(SqlDatabase).to_name('legacy_db', IDatabase)

    main_container = Container('main')
    # register main class and entry point
    main_container.register_callable(main).to_name('main_function'). \
        with_params(num_of_jobs=3, job_type='-example-').with_name_bindings(main_manager='main_class')
    main_container.register_type(MainManager).to_name('main_class'). \
        with_name_bindings(internal_communicator='internal_comm', external_communicator='external_comm')

    comm_container = Container('comm')
    # register communication classes
    comm_container.register_type(InternalCommunicator).to_name('internal_comm', ICommunicator). \
        with_name_bindings(comm_protocol='internal_protocol')
    comm_container.register_type(ExternalCommunicator).to_name('external_comm', ICommunicator). \
        with_name_bindings(comm_protocol='external_protocol')
    comm_container.register_type(UdpCommProtocol, Instantiation.MultiInstance).to_name('internal_protocol',
                                                                                       ICommProtocol)
    comm_container.register_type(HttpCommProtocol, Instantiation.MultiInstance).to_name('external_protocol',
                                                                                        ICommProtocol)

    # setting sub containers
    comm_container.add_sub_container(base_container)
    main_container.add_sub_container(base_container)
    main_container.add_sub_container(comm_container)

    # activating the main function
    main_container.resolve_name('main_function')
