import inspect
import logging
import os
from abc import ABC, abstractmethod, ABCMeta
from collections import deque
from enum import Enum
from typing import Any, Optional, Dict, Type, TypeVar, Callable, Generic, Union, Tuple, Iterable, Sequence, List, Deque, cast

_logger = logging.getLogger(__name__)

T = TypeVar('T')
RegistryKey = Union[Type[T], str]


class DiContainerError(Exception):
    """
    Describes an error in the operation of a container.
    """
    pass


class Instantiation(Enum):
    """
    Defines the instantiation multiplicity for registered types:
        - :code:`Instantiation.Singleton`: A single instance is created on first resolve
          and returned on subsequent resolves.
        - :code:`Instantiation.MultiInstance`: A new instance is created for every resolve.
    """
    Singleton = 0
    MultiInstance = 1


class _Registry(Dict[RegistryKey, 'Register[T]']):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self._sub_registries: Dict[str, '_Registry'] = {}

    def add_sub_registry(self, sub_registry: '_Registry') -> None:
        self._sub_registries[sub_registry.name] = sub_registry

    def remove_sub_registry(self, name: str) -> None:
        self._sub_registries.pop(name)

    def register(self, key: RegistryKey, register: 'Register[T]'):
        self[key] = register

    def __getitem__(self, k: RegistryKey) -> 'Register[T]':
        if super().__contains__(k):  # dict[k]
            return super().__getitem__(k)

        for sub_registry in self._sub_registries.values():
            if k in sub_registry:
                return sub_registry[k]

    def __contains__(self, o: object) -> bool:
        return super().__contains__(o) or any(o in sub_registry for sub_registry in self._sub_registries.values())


class Register(ABC, Generic[T]):
    """
    A registration record. Used to define and configure the details of a registration.
    """

    def __init__(self, registry: _Registry, instantiation: Instantiation, param_names_as_bindings: bool):
        self._is_valid: bool = True
        self._key: RegistryKey = None
        self._registry: _Registry = registry
        self._instantiation: Instantiation = instantiation
        self._param_names_as_bindings: bool = param_names_as_bindings
        self._given_positional_params: Sequence = ()
        self._given_keyword_params: Dict = {}
        self._given_positional_name_bindings: Sequence = ()
        self._given_keyword_name_bindings: Dict = {}
        self._cached_instance: T = None

    @abstractmethod
    def _type_to_check(self) -> Type[T]:
        pass

    @abstractmethod
    def _factory_method(self) -> Callable[..., T]:
        pass

    def _invalidate(self):
        self._is_valid = False
        self._registry.pop(self._key, None)

    def _check_validity(self):
        if not self._is_valid:
            error_msg = f'This Register is not valid anymore. No operations are allowed.'
            _logger.error(error_msg)
            raise DiContainerError(error_msg)

    def _raise_bad_operation_error(self):
        operation = inspect.stack()[1].function
        raise DiContainerError(f'The operation "{operation}" is not supported on "{self.__class__.__name__}" objects.')

    def _check_type(self, type_to_check_against: type):
        """
        :raises TypeError: If the type to check isn't a subclass of the type to check against, otherwise does nothing.
        """
        type_to_check = self._type_to_check()
        if type_to_check is not None and not issubclass(type_to_check, type_to_check_against):
            error_msg = f'The type {type_to_check} is not a subclass of type {type_to_check_against}'
            _logger.error(error_msg)
            raise TypeError(error_msg)

    def _check_only_one_type_of_positional_input(self):
        if self._given_positional_params and self._given_positional_name_bindings:
            self._invalidate()
            error_msg = f'Cannot define both positional params ({self._given_positional_params}) ' \
                        f'and positional name bindings ({self._given_positional_name_bindings}).'
            _logger.error(error_msg)
            raise DiContainerError(error_msg)

    def with_params(self, *positional_params, **keyword_params) -> 'Register[T]':
        """
        Assigns values to arguments of the registered object, provided it's :func:`callable` (types, functions etc.).

        :param positional_params: Values in order of the corresponding arguments, starting from the first.
        :param keyword_params: keyword=value assignments.
        :return: The Register object itself, for fluent interfacing.
        """
        self._check_validity()
        self._given_positional_params = positional_params
        self._check_only_one_type_of_positional_input()
        self._given_keyword_params = keyword_params
        return self

    def with_name_bindings(self, *positional_name_bindings, **keyword_name_bindings) -> 'Register[T]':
        """
        Assigns name bindings to arguments of the registered object,
        provided it's :func:`callable` (types, functions etc.).

        :param positional_name_bindings: positional name_binding assignments,
        where :code:`name_binding` is a name to which a dependency is registered.
        :param keyword_name_bindings: keyword=name_binding assignments,
        where :code:`name_binding` is a name to which a dependency is registered.
        :return: The Register object itself, for fluent interfacing.
        """
        self._check_validity()
        self._given_positional_name_bindings = positional_name_bindings
        self._check_only_one_type_of_positional_input()
        self._given_keyword_name_bindings = keyword_name_bindings
        return self

    def _register_to_key(self, register_key: RegistryKey, type_to_check_against: type, replace: bool = False):
        if self._key is not None:
            error_msg = f'This Register record is already bound to ' \
                        f'"{self._key.__name__ if callable(self._key) else self._key}".' \
                        ' Probably invoked to_type/to_name more than once.'
            _logger.error(error_msg)
            raise DiContainerError(error_msg)
        if register_key in self._registry and not replace:
            error_msg = f'The register key "{register_key.__name__ if callable(register_key) else register_key}"' \
                        f' is already bound to "{self._registry[register_key]._type_to_check().__name__}"' \
                        f' and replace was not requested (replace == False).'
            _logger.error(error_msg)
            raise ValueError(error_msg)
        self._check_type(type_to_check_against)  # may raise TypeError
        self._registry.register(register_key, self)
        self._key = register_key

    def to_type(self, dependency_type: Type[T], *, replace: bool = False) -> 'Register[T]':
        """
        Registers the object in this :class:`Register` to the given dependency type, usually an interface.
        When the dependency type resolved, the object in this :class:`Register` will be used to fulfill the requirement.

        :param dependency_type: The type to be resolved as the object in this Register.
        :param replace: If replace is True and the given dependency type has a registration already,
                        it will be replaced. If False, ValueError is raised.
        :return: The Register object itself, for fluent interfacing.
        :raises DiContainerError: If the object in this Register is being registered more than once.
        :raises ValueError: If the given dependency type has a registration already and replace is False.
        :raises TypeError: If the object in this Register is not a subclass of the given dependency type.
        """
        self._check_validity()
        self._register_to_key(dependency_type, dependency_type, replace)
        return self

    def to_name(self, name: str, base_type: Optional[type] = object, *, replace: bool = False) -> 'Register[T]':
        """
        Registers the object in this :class:`Register` to the given name.

        :param name: The name to be resolved as the object in this Register.
        :param base_type: An optional type to check the object in this Register against.
        :param replace: If replace is True and the given name has a registration already,
                        it will be replaced. If False, ValueError is raised.
        :return: The Register object itself, for fluent interfacing.
        :raises DiContainerError: If the object in this Register is being registered more than once.
        :raises ValueError: If the given name has a registration already and replace is False.
        :raises TypeError: If the object in this Register is not a subclass of the given base type, if given.
        """
        self._check_validity()
        self._register_to_key(name, base_type, replace)
        return self

    def _resolve_param(self, param_name: str, registers_in_resolving_process: Deque['Register'],
                       has_given_value: bool, given_value: Any,
                       has_name_binding: bool, name_binding: str,
                       has_default: bool, default, prefer_defaults: bool,
                       has_annotation: bool, annotation: Union[type, str, None]) -> Tuple[Optional[T], List[str]]:
        value = None
        is_resolved = False
        errors = []
        if has_given_value:
            value = given_value
            is_resolved = True
        elif has_name_binding:
            if name_binding in self._registry:
                value = self._registry[name_binding]._resolve_recursive(errors, registers_in_resolving_process, prefer_defaults=False)
                is_resolved = True
        elif prefer_defaults and has_default:
            value = default
            is_resolved = True
        elif has_annotation:
            param_type = annotation if callable(annotation) else eval(annotation)
            if param_type in self._registry:
                value = self._registry[param_type]._resolve_recursive(errors, registers_in_resolving_process, prefer_defaults=False)
                is_resolved = True
        if value is None:  # Last resort: Using the argument's name as a binding key, or taking the default value, if exists.
            if self._param_names_as_bindings and param_name in self._registry:
                value = self._registry[param_name]._resolve_recursive(errors, registers_in_resolving_process, prefer_defaults=False)
                is_resolved = True
            elif has_default:
                value = default
                is_resolved = True
        if not is_resolved:
            error_desc = f'The parameter "{param_name}" ' \
                         'has no given value, type annotation or default value that is registered, and cannot be resolved.'
            errors.append(error_desc)
        return value, errors

    def _resolve_params(self, prefer_defaults: bool, a_callable: Callable, registers_in_resolving_process: Deque['Register']) -> Tuple[Iterable, Dict, List]:
        arg_values = []
        kwarg_values = {}
        errors = []

        is_type = type(a_callable) in (type, ABCMeta)
        if is_type:
            a_type: type = cast(type, a_callable)
            function = a_type.__init__
        else:
            function = a_callable
        params: inspect.FullArgSpec = inspect.getfullargspec(function)
        if is_type:
            params.args.pop(0)  # removing 'self' param, because it's not a parameter of the constructor

        # handle positional arguments
        for i, arg in enumerate(params.args):
            if i <= len(self._given_positional_params) - 1:  # is there a given value in the i'th place?
                has_given_value = True
                given_value = self._given_positional_params[i]
            elif arg in self._given_keyword_params:
                has_given_value = True
                given_value = self._given_keyword_params[arg]
            else:
                has_given_value = False
                given_value = None

            if i <= len(self._given_positional_name_bindings) - 1:  # is there a given value in the i'th place?
                has_name_binding = True
                name_binding = self._given_positional_name_bindings[i]
            elif arg in self._given_keyword_name_bindings:
                has_name_binding = True
                name_binding = self._given_keyword_name_bindings.get(arg, None)
            else:
                has_name_binding = False
                name_binding = None

            default_index = i - (len(params.args) - len(params.defaults or ()))  # default matching from the end
            has_default = default_index >= 0
            default = params.defaults[default_index] if has_default else None

            has_annotation = arg in params.annotations
            annotation = params.annotations.get(arg, None)

            arg_value, param_errors = self._resolve_param(arg, registers_in_resolving_process,
                                                          has_given_value, given_value,
                                                          has_name_binding, name_binding,
                                                          has_default, default, prefer_defaults,
                                                          has_annotation, annotation)
            arg_values.append(arg_value)
            errors.extend(param_errors)

        # handle vararg (*args)
        if len(self._given_positional_params) > len(params.args):
            if params.varargs is not None:
                arg_values.extend(self._given_positional_params[len(params.args):])
            else:
                error_desc = 'Too many positional arguments given, or vararg (*args) is missing'
                errors.append(error_desc)
        elif len(self._given_positional_name_bindings) > len(params.args):
            if params.varargs is not None:
                arg_values.extend(self._given_positional_params[len(params.args):])
                values = [self._registry[name_binding]._resolve_recursive(errors, registers_in_resolving_process, prefer_defaults=False)
                          for name_binding in self._given_positional_name_bindings[len(params.args):]]
                arg_values.extend(values)
            else:
                error_desc = 'Too many positional name bindings given, or vararg (*args) is missing'
                errors.append(error_desc)

        # handle keyword arguments
        for kwarg in params.kwonlyargs:
            if kwarg in self._given_keyword_params:
                has_given_value = True
                given_value = self._given_keyword_params[kwarg]
            else:
                has_given_value = False
                given_value = None

            has_name_binding = kwarg in self._given_keyword_name_bindings
            name_binding = self._given_keyword_name_bindings.get(kwarg, None)

            has_default = kwarg in (params.kwonlydefaults or ())
            default = params.kwonlydefaults[kwarg] if has_default else None

            has_annotation = kwarg in params.annotations
            annotation = params.annotations.get(kwarg, None)

            kwarg_value, param_errors = self._resolve_param(kwarg, registers_in_resolving_process,
                                                            has_given_value, given_value,
                                                            has_name_binding, name_binding,
                                                            has_default, default, prefer_defaults,
                                                            has_annotation, annotation)
            kwarg_values[kwarg] = kwarg_value
            errors.extend(param_errors)

        # handle varkw (**kwargs) with unused given keyword params
        unused_keywords = set(self._given_keyword_params.keys()) - set(params.args) - set(params.kwonlyargs)
        if unused_keywords:
            if params.varkw is not None:
                kwarg_values.update(self._given_keyword_params)
            else:
                error_desc = f'The given keyword arguments {unused_keywords} are either wrong, ' \
                             'or varkw (**kwargs) is missing'
                errors.append(error_desc)

        # handle varkw (**kwargs) with unused given name bindings
        unused_name_bindings = set(self._given_keyword_name_bindings.keys()) - set(params.args) - set(params.kwonlyargs)
        if unused_name_bindings:
            if params.varkw is not None:
                for kwarg, name_binding in self._given_keyword_name_bindings.items():
                    kwarg_value, param_errors = self._resolve_param(kwarg, registers_in_resolving_process,
                                                                    has_given_value=False, given_value=None,
                                                                    has_name_binding=True, name_binding=name_binding,
                                                                    has_default=False, default=None, prefer_defaults=prefer_defaults,
                                                                    has_annotation=False, annotation=None)
                    kwarg_values[kwarg] = kwarg_value
                    errors.extend(param_errors)
            else:
                error_desc = f'The given name bindings {unused_name_bindings} are either wrong, ' \
                             'or varkw (**kwargs) is missing'
                errors.append(error_desc)
        return arg_values, kwarg_values, errors

    def _resolve(self, registers_in_resolving_process: Deque['Register'], prefer_defaults: bool) -> Tuple[Optional[T], List[str]]:
        """
        :raises DiContainerError: If errors occurred during the resolving process.
        """
        a_callable = self._factory_method()
        if self in registers_in_resolving_process:
            errors = [f"{a_callable.__name__}'s registration to {self._key if type(self._key) is str else self._key.__name__} "
                      'has a circular dependency on itself. Set the problematic parameter explicitly.']
            value = None
        else:
            registers_in_resolving_process.append(self)
            arg_values, kwarg_values, errors = self._resolve_params(prefer_defaults, a_callable, registers_in_resolving_process)
            if errors:
                error_str = f'Errors while trying to resolve parameters for "{a_callable.__name__}" ' \
                            f'in container "{self._registry.name}": [\n{(os.linesep + ",").join(errors)}\n]'
                raise DiContainerError(error_str)
            value = a_callable(*arg_values, **kwarg_values)
            registers_in_resolving_process.pop()
        return value, errors

    def _resolve_recursive(self, errors: List[str], registers_in_resolving_process: Deque['Register'], prefer_defaults: bool) -> T:
        """
        :raises DiContainerError: If errors occurred during the resolving process.
        """
        if self._cached_instance is None or self._instantiation is Instantiation.MultiInstance:
            self._cached_instance, sub_errors = self._resolve(registers_in_resolving_process, prefer_defaults)
            errors.extend(sub_errors)
        return self._cached_instance

    def resolve(self, prefer_defaults: bool = False) -> T:
        """
        Resolves the object in this :class:`Register`. This is done in this order:
         #. Returns a cached value, if exists, either because of value registration,
            or an `Instantiation.Singleton` multiplicity that was already resolved.
         #. Resolves the needed arguments and calls the object in this :class:`Register` with them. For each argument, the resolve order is thus:
             #. A manual assignment is used, if one was given via :func:`with_params`.
             #. An explicit name binding is used for lookup in the class:`Container`, if one was given via :func:`with_name_bindings`.
             #. The type annotation of the argument is used for lookup in the class:`Container`, if it exists.
             #. The default value of the argument is used, if it exists.
             #. The argument's name is used as a name binding for lookup in the class:`Container`, if its :code:`param_names_as_bindings` is :code:`True`.

        :param prefer_defaults: Whether to prefer default values for arguments over resolving from the class:`Container`, or not.
        :return: The resolved value.
        :raises DiContainerError: If errors occurred during the resolving process.
        """
        self._check_validity()
        return self._resolve_recursive(prefer_defaults=prefer_defaults, errors=[], registers_in_resolving_process=deque())


class CallableRegister(Register):
    def __init__(self, registry: _Registry, function: Callable[..., T], instantiation: Instantiation,
                 return_type: Type[T], param_names_as_bindings: bool):
        super().__init__(registry, instantiation, param_names_as_bindings)
        self._function = function
        self._return_type = return_type

    def _type_to_check(self) -> Type[T]:
        return self._return_type

    def _factory_method(self) -> Callable[..., T]:
        return self._function


class TypeRegister(CallableRegister):
    def __init__(self, registry: _Registry, concrete_type: Type[T], instantiation: Instantiation,
                 param_names_as_bindings: bool):
        super().__init__(registry, concrete_type, instantiation, concrete_type, param_names_as_bindings)


class ValueRegister(Register):
    def __init__(self, registry: _Registry, value: Any):
        super().__init__(registry, Instantiation.Singleton, param_names_as_bindings=False)
        self._cached_instance = value

    def _type_to_check(self) -> Type[T]:
        return type(self._cached_instance)

    def _factory_method(self):
        self._raise_bad_operation_error()

    def with_params(self, *positional_params, **keyword_params):
        self._raise_bad_operation_error()

    def with_name_bindings(self, **keyword_name_bindings):
        self._raise_bad_operation_error()


class Container:
    """
    Contains registered objects, to be resolved explicitly, or implicitly as part of argument resolving.
    """

    def __init__(self, name: str, *, param_names_as_bindings: bool = True) -> None:
        self.name: str = name
        self._sub_containers: Dict[str, 'Container'] = {}
        self._registry: _Registry = _Registry(self.name)
        self._param_names_as_bindings: bool = param_names_as_bindings

    def register_type(self, concrete_type: Type[T],
                      instantiation: Instantiation = Instantiation.Singleton) -> Register[T]:
        """
        Creates a :class:`Register` record for the given type,
        so that it can be configured and registered into this :class:`Container`.

        :param concrete_type: The actual type to be instantiated when resolving.
        :param instantiation: The instantiation multiplicity.
                                Instantiation.Singleton for one time instantiation and caching.
                                Instantiation.MultiInstance for new instantiation on every resolve.
        :return: A Register object that represents the given concrete type.
        """
        return TypeRegister(self._registry, concrete_type, instantiation, self._param_names_as_bindings)

    def register_callable(self, a_callable: Callable, instantiation: Instantiation = Instantiation.Singleton,
                          return_type: Optional[Type[T]] = None) -> Register[T]:
        """
        Creates a :class:`Register` record for the given callable,
        so that it can be configured and registered into this :class:`Container`.

        :param a_callable: The callable to be invoked when resolving.
        :param instantiation: The instantiation multiplicity.
                                Instantiation.Singleton for one time invocation and caching.
                                Instantiation.MultiInstance for new invocation on every resolve.
        :param return_type: The given callable's return type, for type checking. Optional.
        :return: A Register object that represents the given concrete type.
        """
        return CallableRegister(self._registry, a_callable, instantiation, return_type, self._param_names_as_bindings)

    def register_value(self, value: Any) -> Register[T]:
        """
        Creates a :class:`Register` record for the given value,
        so that it can be configured and registered into this :class:`Container`.

        :param value: The value to be returned when resolving.
        :return: A Register object that represents the given concrete type.
        """
        return ValueRegister(self._registry, value)

    def _check_for_circular_sub_containers(self, new_sub_container: 'Container') -> bool:
        def _check_for_circular_sub_containers_recursive(src_container: 'Container',
                                                         dst_container: 'Container') -> bool:
            if dst_container in src_container._sub_containers.values():
                return True
            for sub_container in src_container._sub_containers.values():
                if _check_for_circular_sub_containers_recursive(sub_container, dst_container):
                    return True
            return False

        return _check_for_circular_sub_containers_recursive(new_sub_container, self)

    def add_sub_container(self, sub_container: 'Container') -> None:
        """
        Adds the given :class:`Container` as a sub-container, to be searched in the lookup process of resolving.
        The lookup process starts with the current :class:`Container`
        and then looks up in sub-containers in the order the were added, recursively.

        :param sub_container: The container to be added as a sub-container.
        """
        if self._check_for_circular_sub_containers(sub_container):
            raise DiContainerError(f'Adding the sub container "{sub_container.name}" to the container "{self.name}" '
                                   f'will create a circular chain of containers')
        self._sub_containers[sub_container.name] = sub_container
        self._registry.add_sub_registry(sub_container._registry)

    def remove_sub_container(self, sub_container_name: str) -> None:
        """
        Removes the :class:`Container` with the given name from the list of sub-containers.

        :param sub_container_name: The name of the sub-container to remove.
        """
        self._sub_containers.pop(sub_container_name)
        self._registry.remove_sub_registry(sub_container_name)

    def _resolve(self, registry_key: RegistryKey, prefer_defaults: bool) -> Any:
        register: Register[T] = self._registry.get(registry_key, None)
        if register is None:
            error_msg = f'The key {registry_key} is not registered in this container ({self.name})'
            _logger.error(error_msg)
            raise ValueError(error_msg)
        else:
            instance = register.resolve(prefer_defaults)
        return instance

    def resolve_type(self, dependency_type: Type[T], prefer_defaults: bool = False) -> Optional[T]:
        """
        Resolves the given dependency type to an appropriate value, according to the content of this :class:`Container`.

        :param dependency_type: The type to be resolved into a value.
        :param prefer_defaults: If :code:`True`, arguments that were given no explicit values or bindings,
        will be fulfilled by their defaults first, if available.
        :return: The resolved value, of appropriate type (a subclass of the dependency type).
        :raises ValueError: If the given type is not registered in this Container.
        """
        return self._resolve(dependency_type, prefer_defaults)

    def resolve_name(self, name: str, prefer_defaults: bool = False) -> Any:
        """
        Resolves the given name to a value, according to the content of this Container.

        :param name: The name to be resolved into a value.
        :param prefer_defaults: If :code:`True`, arguments that were given no explicit values or bindings,
        will be fulfilled by their defaults first, if available.
        :return: The resolved value.
        :raises ValueError: If the given name is not registered in this Container.
        """
        return self._resolve(name, prefer_defaults)
