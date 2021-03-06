from pytest_bdd import scenarios, given, when, then, parsers
import pytest

scenarios("features/single_run.feature")


@given(parsers.parse("a pwscf object setup as follows\n{text}"))
def pwscf(text):
    from quantities import Ry
    from pylada.espresso import Pwscf
    pwscf = Pwscf()
    exec(text, globals(), {'pwscf': pwscf, 'Ry': Ry})
    return pwscf


@given(parsers.parse("a fake pseudo '{filename}' in the working directory"))
def pseudo_filename(tmpdir, filename):
    tmpdir.join(filename).ensure(file=True)
    return tmpdir.join(filename)


@given("an aluminum structure")
def aluminum():
    from quantities import bohr_radius
    from pylada.crystal.bravais import fcc
    result = fcc()
    result.scale = 7.5 * bohr_radius
    result[0].type = 'Al'
    return result


@given("a serial communicator")
def serialcomm():
    return {'n': 1}


@pytest.fixture
def passon():
    """ A container to pass information from when to then """
    return []


@pytest.fixture
def true(tmpdir):
    from sys import executable
    from stat import S_IREAD, S_IWRITE, S_IEXEC
    result = tmpdir.join("true.py")
    result.write("#! %s\nfrom sys import exit\nexit(0)" % executable)
    result.chmod(S_IREAD | S_IWRITE | S_IEXEC)
    return result

@when("iterating through the first step")
def first_step(pwscf, tmpdir, aluminum, passon, true):
    from six import next
    iterator = pwscf.iter(aluminum, tmpdir, program=str(true))
    passon.extend([iterator, next(iterator)])


@when("executing the program process")
def execute_program(passon, serialcomm):
    passon[-1].start({'n': 1})
    passon[-1].wait()


@when("iterating through the second step")
def second_step(passon):
    from six import next
    iterator = passon[0]
    passon.append(next(iterator))


@when("running pwscf")
def run_nonscf(tmpdir, aluminum, pwscf, passon):
    from pylada.espresso.tests.bdd.fixtures import copyoutput, data_path
    src = data_path("nonscf")
    program = copyoutput(tmpdir, src, tmpdir)
    passon.append(pwscf(aluminum, tmpdir, program=str(program)))


@then("the yielded object is a ProgrammProcess")
def first_yield(passon):
    from pylada.process import ProgramProcess
    iterator, first_step = passon
    assert isinstance(first_step, ProgramProcess)


@then("the yielded object is an Extract object")
def second_yield(passon):
    from pylada.espresso.extract import Extract
    extract = passon[-1]
    assert isinstance(extract, Extract)


@then(parsers.parse("a valid {filename} exists"))
def check_pwscf_input(tmpdir, filename, pwscf):
    from pylada.espresso import Pwscf
    actual = Pwscf()
    actual.read(tmpdir.join(filename))
    assert abs(actual.system.ecutwfc - pwscf.system.ecutwfc) < 1e-8
    assert actual.kpoints.subtitle == pwscf.kpoints.subtitle
    assert actual.kpoints.value.rstrip().lstrip() == pwscf.kpoints.value.rstrip().lstrip()


@then("the extract object says the run is unsuccessful")
def unsuccessfull_run(passon):
    extract = passon[-1]
    assert extract.success == False


@then(parsers.parse("the marker file '{filename}' exists"))
def check_marker_file(tmpdir, filename):
    assert tmpdir.join(filename).check(file=True)


@then(parsers.parse("the output file '{filename}' exists"))
def check_output_file(tmpdir, filename):
    assert tmpdir.join(filename).check(file=True)


@then(parsers.parse("the error file '{filename}' exists"))
def check_error_file(tmpdir, filename):
    assert tmpdir.join(filename).check(file=True)


@then(parsers.parse("the marker file '{filename}' has been removed"))
def check_marker_file_disappeared(tmpdir, filename):
    assert tmpdir.join(filename).check(file=False)


@then("the run is successful")
def result_nonscf(passon):
    from pylada.espresso.extract import Extract
    assert isinstance(passon[0], Extract)
    assert passon[0].success
