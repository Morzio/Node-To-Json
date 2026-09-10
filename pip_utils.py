from sys import executable
from subprocess import check_call, check_output
from packaging import version
from pathlib import Path
from operator import itemgetter


def pip_install(package_name):
    check_call([executable, "-m", "pip", "install", package_name])


def pip_uninstall(package_name):
    check_call([executable, "-m", "pip", "uninstall", package_name, "-y"])


def get_pip_data():
    installed = check_output([executable, "-m", "pip", "freeze"]).decode('utf-8')
    return (i.split("==")[:2] if "==" in i else i.split(" ")[:2] for i in installed.split("\r\n")[:-1])


def pip_list():
    return map(itemgetter(0), get_pip_data())


def pip_dict():
    return dict(get_pip_data())


def get_package_version(package_name):
    return pip_dict().get(package_name)


def split_version(ver):
    try:
        v = version.parse(ver)
        return [v.major, v.minor, v.micro]
    except:
        return


def is_version_greater(ver, other_ver):
    v1 = version.parse(ver)
    v2 = version.parse(other_ver)
    return v1 > v2


def not_installed(name):
    return name not in pip_list()


def read_requirements(req_dir):
    with open(str(Path(req_dir).joinpath("requirements.txt")), 'r') as f:
        for line in f:
            yield line.split("\n")[0]


def requirements_not_installed_mask(req_dir):
    pl = set(pip_list())
    req_pkg = read_requirements(req_dir)
    return (name not in pl for name in req_pkg)


def requirements_not_installed_dict(req_dir):
    pl = set(pip_list())
    req_pkg = read_requirements(req_dir)
    return {name: name not in pl for name in req_pkg}


def pip_install_wheel_from(package_name, source_dir):
    check_call([executable, "-m", "pip", "install", '--no-index', f'--find-links={str(source_dir)}', package_name])


def pip_install_wheel_from_requirements(source_dir, req_dir=None):
    if req_dir == None:
        req_dir = source_dir
    check_call([executable, "-m", "pip", "install", '--no-index', f'--find-links={str(source_dir)}', '-r', f'{str(Path(req_dir).joinpath("requirements.txt"))}'])
