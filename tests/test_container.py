from typing import Optional

import pytest

from di_container.container import Container, Instantiation, DiContainerError


# region fixtures
@pytest.fixture()
def container():
    # setup
    c = Container('main')

    yield c

    # teardown
    del c


@pytest.fixture()
def container_no_implicit():
    # setup
    c = Container('main', param_names_as_bindings=False)

    yield c

    # teardown
    del c


@pytest.fixture()
def sub_container():
    # setup
    c = Container('sub')

    yield c

    # teardown
    del c


# endregion fixtures


# region classes etc. for testing
class Base:
    pass


class A(Base):
    pass


class B(Base):
    pass


def factory_of_base(type_name: str = 'A') -> Base:
    if type_name == 'A':
        return A()
    if type_name == 'B':
        return B()


class MultipleArgs:
    def __init__(self, a: int, b: int, c: int, d: int):
        self.a = a
        self.b = b
        self.c = c
        self.d = d


class VarArgsAndKWArgs:
    def __init__(self, *args, **kwargs):
        self.varargs = [arg for arg in args]
        self.kwargs = {k: v for k, v in kwargs.items()}


class KWOnlyArgs:
    def __init__(self, a: int, b: int, *, c: int, d: int):
        self.a = a
        self.b = b
        self.c = c
        self.d = d


class DependantWithTypeHints:
    def __init__(self, base: Base):
        self.base = base


class DependantWithoutTypeHints:
    def __init__(self, base):
        self.base = base


class Circle1:
    pass


class Circle2:
    @staticmethod
    def independent_circle2():
        return Circle2(None)


class Circle3:
    pass


def circle1_init(self, circle: Circle2):
    self.circle = circle


def circle2_init(self, circle: Circle3):
    self.circle = circle


def circle3_init(self, circle: Circle1):
    self.circle = circle


Circle1.__init__ = circle1_init
Circle2.__init__ = circle2_init
Circle3.__init__ = circle3_init


class DependenciesOfSameType:
    def __init__(self, param1: Base, param2: Base):
        self.param1 = param1
        self.param2 = param2


class DependantWithOptional:
    def __init__(self, a: Optional[A] = None):
        self.a = a


# endregion classes etc. for testing


# region test basic registrations
def test_register_type_to_type_correct(container: Container):
    container.register_type(A).to_type(Base)
    assert type(container.resolve_type(Base)) is A


def test_register_type_to_type_wrong_type(container: Container):
    with pytest.raises(TypeError):
        container.register_type(dict).to_type(list)


def test_register_type_to_name_correct(container: Container):
    container.register_type(A).to_name('An_A', base_type=Base)
    assert type(container.resolve_name('An_A')) is A


def test_register_type_to_name_wrong_type(container: Container):
    with pytest.raises(TypeError):
        container.register_type(dict).to_name('A_Dict', base_type=list)


def test_register_callable_to_type_with_params_correct(container: Container):
    container.register_callable(factory_of_base, return_type=Base).to_type(Base).with_params('A')
    assert type(container.resolve_type(Base)) is A


def test_register_callable_to_type_with_params_correct_kw(container: Container):
    container.register_callable(factory_of_base, return_type=Base).to_type(Base).with_params(type_name='A')
    assert type(container.resolve_type(Base)) is A


def test_register_callable_to_type_with_params_wrong_type(container: Container):
    with pytest.raises(TypeError):
        container.register_callable(factory_of_base, return_type=Base).to_type(list).with_params('A')


def test_register_callable_to_name_with_params_correct(container: Container):
    container.register_callable(factory_of_base, return_type=Base).to_name('Some_B', base_type=Base).with_params('B')
    assert type(container.resolve_name('Some_B')) is B


def test_register_callable_to_name_with_params_wrong_type(container: Container):
    with pytest.raises(TypeError):
        container.register_callable(factory_of_base, return_type=Base).to_name('An_A', base_type=list).with_params('A')


def test_register_value_to_type_correct(container: Container):
    test_int = 1234
    container.register_value(test_int).to_type(int)
    assert container.resolve_type(int) == test_int


def test_register_value_to_type_wrong_type(container: Container):
    test_str = '1234'
    with pytest.raises(TypeError):
        container.register_value(test_str).to_type(int)


def test_register_value_to_name_correct(container: Container):
    test_int = 1234
    container.register_value(test_int).to_name('An_Int', base_type=int)
    assert container.resolve_name('An_Int') == test_int


def test_register_value_to_name_wrong_type(container: Container):
    test_str = '1234'
    with pytest.raises(TypeError):
        container.register_value(test_str).to_name('An_Int', base_type=int)


# endregion test basic registrations


# region test registration nuances
def test_register_singleton(container: Container):
    container.register_type(A, instantiation=Instantiation.Singleton).to_type(Base)
    a1 = container.resolve_type(Base)
    a2 = container.resolve_type(Base)
    assert a1 is a2
    assert type(a1) is A


def test_register_multi_instance(container: Container):
    container.register_type(A, instantiation=Instantiation.MultiInstance).to_type(Base)
    a1 = container.resolve_type(Base)
    a2 = container.resolve_type(Base)
    assert a1 is not a2
    assert type(a1) is type(a2) is A


def test_register_type_duplicate(container: Container):
    container.register_type(A).to_type(Base)
    with pytest.raises(ValueError):
        container.register_type(B).to_type(Base)
    assert type(container.resolve_type(Base)) is A
    container.register_type(B).to_type(Base, replace=True)
    assert type(container.resolve_type(Base)) is B


def test_register_twice_type_type(container: Container):
    with pytest.raises(DiContainerError):
        container.register_type(A).to_type(Base).to_type(Base)


def test_register_twice_type_name(container: Container):
    with pytest.raises(DiContainerError):
        container.register_type(A).to_type(Base).to_name('Base')


def test_register_twice_name_type(container: Container):
    with pytest.raises(DiContainerError):
        container.register_type(A).to_name('Base').to_type(Base)


def test_register_twice_name_name(container: Container):
    with pytest.raises(DiContainerError):
        container.register_type(A).to_name('Base').to_name('Base')


def test_register_with_multiple_args(container: Container):
    container.register_type(MultipleArgs).to_type(MultipleArgs).with_params(1, 2, 3, 4)
    multiple_args = container.resolve_type(MultipleArgs)
    assert type(multiple_args) is MultipleArgs
    assert multiple_args.a == 1 and multiple_args.b == 2 and multiple_args.c == 3 and multiple_args.d == 4


def test_register_with_multiple_kwargs(container: Container):
    container.register_type(MultipleArgs).to_type(MultipleArgs).with_params(a=1, b=2, c=3, d=4)
    multiple_args = container.resolve_type(MultipleArgs)
    assert type(multiple_args) is MultipleArgs
    assert multiple_args.a == 1 and multiple_args.b == 2 and multiple_args.c == 3 and multiple_args.d == 4


def test_register_with_multiple_args_and_kwargs(container: Container):
    container.register_type(MultipleArgs).to_type(MultipleArgs).with_params(1, 2, c=3, d=4)
    multiple_args = container.resolve_type(MultipleArgs)
    assert type(multiple_args) is MultipleArgs
    assert multiple_args.a == 1 and multiple_args.b == 2 and multiple_args.c == 3 and multiple_args.d == 4


def test_register_with_too_many_args(container: Container):
    container.register_type(MultipleArgs).to_type(MultipleArgs).with_params(1, 2, 3, 4, 5)
    with pytest.raises(DiContainerError):
        container.resolve_type(MultipleArgs)


def test_register_with_wrong_kwargs(container: Container):
    container.register_type(MultipleArgs).to_type(MultipleArgs).with_params(a=1, b=2, c=3, d=4, e=5)
    with pytest.raises(DiContainerError):
        container.resolve_type(MultipleArgs)


def test_register_with_varargs(container: Container):
    container.register_type(VarArgsAndKWArgs).to_type(VarArgsAndKWArgs).with_params(1, 2, 3, 4)
    varargs_and_kwargs = container.resolve_type(VarArgsAndKWArgs)
    assert type(varargs_and_kwargs) is VarArgsAndKWArgs
    assert varargs_and_kwargs.varargs == [1, 2, 3, 4]
    assert varargs_and_kwargs.kwargs == {}


def test_register_with_kwargs(container: Container):
    container.register_type(VarArgsAndKWArgs).to_type(VarArgsAndKWArgs).with_params(a=1, b=2, c=3, d=4)
    varargs_and_kwargs = container.resolve_type(VarArgsAndKWArgs)
    assert varargs_and_kwargs.varargs == []
    assert varargs_and_kwargs.kwargs == {'a': 1, 'b': 2, 'c': 3, 'd': 4}


def test_register_with_varargs_and_kwargs(container: Container):
    container.register_type(VarArgsAndKWArgs).to_type(VarArgsAndKWArgs).with_params(1, 2, c=3, d=4)
    varargs_and_kwargs = container.resolve_type(VarArgsAndKWArgs)
    assert type(varargs_and_kwargs) is VarArgsAndKWArgs
    assert varargs_and_kwargs.varargs == [1, 2]
    assert varargs_and_kwargs.kwargs == {'c': 3, 'd': 4}


def test_register_with_multiple_args_and_name_bindings(container: Container):
    container.register_type(MultipleArgs).to_type(MultipleArgs).with_name_bindings('one', 'two', 'three', 'four')
    container.register_value(1).to_name('one')
    container.register_value(2).to_name('two')
    container.register_value(3).to_name('three')
    container.register_value(4).to_name('four')
    multiple_args = container.resolve_type(MultipleArgs)
    assert type(multiple_args) is MultipleArgs
    assert multiple_args.a == 1 and multiple_args.b == 2 and multiple_args.c == 3 and multiple_args.d == 4


def test_register_with_varargs_and_name_bindings(container: Container):
    container.register_type(VarArgsAndKWArgs).to_type(VarArgsAndKWArgs).with_name_bindings('one', 'two', 'three')
    container.register_value(1).to_name('one')
    container.register_value(2).to_name('two')
    container.register_value(3).to_name('three')
    varargs_and_kwargs = container.resolve_type(VarArgsAndKWArgs)
    assert type(varargs_and_kwargs) is VarArgsAndKWArgs
    assert varargs_and_kwargs.varargs == [1, 2, 3]
    assert varargs_and_kwargs.kwargs == {}


def test_register_with_kwargs_and_name_bindings(container: Container):
    container.register_type(VarArgsAndKWArgs).to_type(VarArgsAndKWArgs).with_name_bindings(a='one', b='two', c='three')
    container.register_value(1).to_name('one')
    container.register_value(2).to_name('two')
    container.register_value(3).to_name('three')
    varargs_and_kwargs = container.resolve_type(VarArgsAndKWArgs)
    assert varargs_and_kwargs.varargs == []
    assert varargs_and_kwargs.kwargs == {'a': 1, 'b': 2, 'c': 3}


def test_register_with_varargs_and_kwargs_and_name_bindings(container: Container):
    container.register_type(VarArgsAndKWArgs).to_type(VarArgsAndKWArgs).with_name_bindings('one', 'two', c='three', d='four')
    container.register_value(1).to_name('one')
    container.register_value(2).to_name('two')
    container.register_value(3).to_name('three')
    container.register_value(4).to_name('four')
    varargs_and_kwargs = container.resolve_type(VarArgsAndKWArgs)
    assert varargs_and_kwargs.varargs == [1, 2]
    assert varargs_and_kwargs.kwargs == {'c': 3, 'd': 4}


def test_register_with_varargs_and_kwargs_and_params_and_name_bindings(container: Container):
    container.register_type(VarArgsAndKWArgs).to_type(VarArgsAndKWArgs).with_params(a=1, b=2).with_name_bindings('three', 'four')
    container.register_value(1).to_name('one')
    container.register_value(2).to_name('two')
    container.register_value(3).to_name('three')
    container.register_value(4).to_name('four')
    varargs_and_kwargs = container.resolve_type(VarArgsAndKWArgs)
    assert varargs_and_kwargs.varargs == [3, 4]
    assert varargs_and_kwargs.kwargs == {'a': 1, 'b': 2}


def test_register_error_params_and_name_bindings_varargs(container: Container):
    with pytest.raises(DiContainerError):
        container.register_type(VarArgsAndKWArgs).to_type(VarArgsAndKWArgs).with_params(1, 2).with_name_bindings('three', 'four')
    with pytest.raises(DiContainerError):
        container.register_type(VarArgsAndKWArgs).to_type(VarArgsAndKWArgs).with_name_bindings('three', 'four').with_params(1, 2)


def test_register_with_kwonlyargs(container: Container):
    container.register_type(KWOnlyArgs).to_type(KWOnlyArgs).with_params(1, 2, c=3, d=4)
    kwonly_args = container.resolve_type(KWOnlyArgs)
    assert type(kwonly_args) is KWOnlyArgs
    assert kwonly_args.a == 1 and kwonly_args.b == 2 and kwonly_args.c == 3 and kwonly_args.d == 4


def test_register_with_missing_kwonlyargs(container: Container):
    container.register_type(KWOnlyArgs).to_type(KWOnlyArgs).with_params(1, 2, c=3)
    with pytest.raises(DiContainerError):
        container.resolve_type(KWOnlyArgs)


# endregion test registration nuances


# region test resolving nuances
def test_resolve_type_not_registered(container: Container):
    with pytest.raises(ValueError):
        container.resolve_type(Base)


def test_resolve_name_not_registered(container: Container):
    with pytest.raises(ValueError):
        container.resolve_name('DEPENDENCY')


def test_resolve_implicit_params_type_annotation_correct(container: Container):
    container.register_type(DependantWithTypeHints).to_name('DEPENDANT')
    container.register_type(A).to_type(Base)
    dependant: DependantWithTypeHints = container.resolve_name('DEPENDANT')
    assert type(dependant) is DependantWithTypeHints
    assert type(dependant.base) is A


def test_resolve_implicit_params_type_annotation_missing_annotation(container: Container):
    container.register_type(DependantWithoutTypeHints).to_name('DEPENDANT')
    container.register_type(A).to_type(Base)
    with pytest.raises(DiContainerError):
        container.resolve_name('DEPENDANT')


def test_resolve_implicit_params_param_name_as_binding_correct(container: Container):
    container.register_type(DependantWithoutTypeHints).to_name('DEPENDANT')
    container.register_type(A).to_name('base')
    dependant: DependantWithoutTypeHints = container.resolve_name('DEPENDANT')
    assert type(dependant) is DependantWithoutTypeHints
    assert type(dependant.base) is A


def test_resolve_implicit_params_param_name_as_binding_not_allowed(container_no_implicit: Container):
    container_no_implicit.register_type(DependantWithoutTypeHints).to_name('DEPENDANT')
    container_no_implicit.register_type(A).to_name('base')
    with pytest.raises(DiContainerError):
        container_no_implicit.resolve_name('DEPENDANT')


def test_resolve_implicit_params_param_name_as_binding_explicit_binding_type(container_no_implicit: Container):
    container_no_implicit.register_type(DependantWithoutTypeHints).to_name('DEPENDANT').with_name_bindings(base=Base)
    container_no_implicit.register_type(A).to_type(Base)
    dependant: DependantWithoutTypeHints = container_no_implicit.resolve_name('DEPENDANT')
    assert type(dependant) is DependantWithoutTypeHints
    assert type(dependant.base) is A


def test_resolve_implicit_params_param_name_as_binding_explicit_binding_name(container_no_implicit: Container):
    container_no_implicit.register_type(DependantWithoutTypeHints).to_name('DEPENDANT').with_name_bindings(base='base')
    container_no_implicit.register_type(A).to_name('base')
    dependant: DependantWithoutTypeHints = container_no_implicit.resolve_name('DEPENDANT')
    assert type(dependant) is DependantWithoutTypeHints
    assert type(dependant.base) is A


def test_resolve_default_as_fallback(container):
    container.register_callable(factory_of_base).to_type(Base)
    assert type(container.resolve_type(Base)) is A


def test_resolve_prefer_defaults(container):
    container.register_callable(factory_of_base, instantiation=Instantiation.MultiInstance).to_name('factory')
    container.register_value('B').to_name('type_name')
    assert type(container.resolve_name('factory')) is B
    assert type(container.resolve_name('factory', prefer_defaults=True)) is A


def test_circular_registration(container: Container):
    container.register_type(Circle1).to_type(Circle1)
    container.register_type(Circle2).to_type(Circle2)
    container.register_type(Circle3).to_type(Circle3)
    with pytest.raises(DiContainerError):
        container.resolve_type(Circle1)
    circle2: Circle2 = Circle2.independent_circle2()
    container.register_type(Circle2).to_type(Circle2, replace=True).with_params(circle=circle2)
    assert type(container.resolve_type(Circle1)) is Circle1


def test_registration_with_same_type_not_circular(container: Container):
    container.register_type(Base).to_name('param1')
    container.register_type(Base).to_name('param2')
    container.register_type(DependenciesOfSameType).to_type(DependenciesOfSameType)
    assert type(container.resolve_type(DependenciesOfSameType)) is DependenciesOfSameType


def test_registration_with_optional_parameters(container: Container):
    container.register_type(DependantWithOptional, instantiation=Instantiation.MultiInstance).to_type(DependantWithOptional)
    dependant: DependantWithOptional = container.resolve_type(DependantWithOptional)
    assert dependant.a is None
    container.register_type(A).to_type(A)
    dependant: DependantWithOptional = container.resolve_type(DependantWithOptional)
    assert type(dependant.a) is A


# endregion test resolving nuances


# region test sub-containers
def test_sub_container_correct(container: Container, sub_container: Container):
    sub_container.register_type(A).to_type(Base)
    container.register_type(DependantWithTypeHints).to_name('DEPENDANT')
    container.add_sub_container(sub_container)
    dependant: DependantWithTypeHints = container.resolve_name('DEPENDANT')
    assert type(dependant) is DependantWithTypeHints
    assert type(dependant.base) is A


def test_sub_container_circular_chain(container: Container, sub_container: Container):
    sub_container.register_type(A).to_type(Base)
    container.register_type(DependantWithTypeHints).to_name('DEPENDANT')
    container.add_sub_container(sub_container)
    with pytest.raises(DiContainerError):
        sub_container.add_sub_container(container)


def test_sub_container_current_before_sub(container: Container, sub_container: Container):
    sub_container.register_type(A).to_type(Base)
    container.register_type(B).to_type(Base)
    container.register_type(DependantWithTypeHints).to_name('DEPENDANT')
    container.add_sub_container(sub_container)
    dependant: DependantWithTypeHints = container.resolve_name('DEPENDANT')
    assert type(dependant) is DependantWithTypeHints
    assert type(dependant.base) is B

# endregion test sub-containers
