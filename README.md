## Dependency Injection Container
### Full featured, flexible and fluent IoC solution for Python

#### PyPi
di_container can be installed from [PyPi](https://pypi.org/project/di-container/). 

#### The Code

##### Basics:
Types, callables and values can be registered into a container and bound to either a dependency type, or a name.
Registration is independent of dependency order: A dependency can be registered after the dependent type, as long as they are both registered before resolving.
```python
from di_container.container import Container

container = Container(name='container')

container.register_callable(main).to_name('main_func')
container.register_value(app_config['logging']['log_path']).to_name('log_path')
container.register_type(FileLogger).to_type(ILogger)
```

##### Multiplicity:
Types and callables can be registered as `Instantiation.Singleton` (default), or as `Instantiation.MultiInstance`.
```python
from di_container.container import Container, Instantiation

container = Container(name='container')

container.register_callable(ConnectionFactory.new_udp_connection, instantiation=Instantiation.MultiInstance).to_type(IConnection)
```

##### Type checks:
Registering `to_type` type checks against the given dependency type. When registering `to_name`, an optional type can be given, in order to make the same check.
If the check fails, a `TypeError` is raised.
```python
from di_container.container import Container

container = Container(name='container')

container.register_value(app_config['network']['http_port']).to_name('port', int)
```

##### Manual assignment:
Type initializers and callables can have some, or all, of their arguments assigned values explicitly.
The rest will be resolved at resolve time.
```python
from di_container.container import Container, Instantiation

container = Container(name='container')

container.register_callable(ConnectionFactory.new_udp_connection, instantiation=Instantiation.MultiInstance).to_type(IConnection).with_params(host='localhost', port=12345)
```

##### Resolving order:
Resolving a registered type, or name, will attempt to resolve any needed arguments for type initializers, or callables, recursively.
First, with values given in `with_params`, second, with declared default values, and then, with arguments' type annotations (please use them ).

When a dependency is registered `to_name`, it cannot be automatically inferred by type annotation.
A container's default behavior is to use an argument's name to lookup a `to_name` registration as a last attempt to resolve an argument.
This behavior can be changed if it's deemed to be too risky, and dependency names can be assigned explicitly when needed.
```python
from di_container.container import Container, Instantiation

container = Container(name='container', param_names_as_bindings=False)

container.register_callable(ConnectionFactory.new_udp_connection, instantiation=Instantiation.MultiInstance).to_type(IConnection).with_name_bindings(host='host_ip', port='port')
container.register_value(app_config['network']['ip']).to_name('host_ip', str)
container.register_value(app_config['network']['http_port']).to_name('port', int)
```

##### Sub-containers:
Sub-containers can help when writing several packages, or sub-systems, or just to organize a large amount of dependencies.
The resolving process will try to resolve from the current container and if no match is found, will try to resolve using each sub-container (and its sub-containers recursively) in the order they were added.
Containers are initialized with names for identification in error messages.
```python
from di_container.container import Container

base_container = Container(name='base')
# register config values and core classes
base_container.register_value(app_config['logging']['log_path']).to_name('log_path')
base_container.register_value(app_config['database']['database_url']).to_name('database_url', str)
base_container.register_type(FileLogger).to_type(ILogger)
base_container.register_type(NoSqlDatabase).to_type(IDatabase)

main_container = Container('main')
# register main class and entry point
main_container.register_callable(main).to_name('main_function').with_name_bindings(main_manager='main_class')
main_container.register_type(MainManager).to_name('main_class').with_name_bindings(internal_comm='int_comm', external_comm='ext_comm')

comm_container = Container('comm')
# register communication classes
comm_container.register_type(UdpCommunicator).to_name('int_comm', ICommunicator)
comm_container.register_type(HttpCommunicator).to_name('ext_comm', ICommunicator)

# setting sub containers
comm_container.add_sub_container(base_container)
main_container.add_sub_container(base_container)
main_container.add_sub_container(comm_container)

# activating the main function
main_container.resolve_name('main_function')
```

#### To Do
Some features that are being considered:
1. Configuration registration.
1. Binding to members of registered items.
1. Registration of collections of values.
1. Display of dependency tree (forest).

#### More
* An [example](http://github.com/eyaldror/di_container/tree/master/example) is available in the git repository.
