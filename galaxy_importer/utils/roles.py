import datetime
import glob
import os
import subprocess
import yaml


def get_path_git_root(path):
    cmd = 'git rev-parse --show-toplevel'
    pid = subprocess.run(cmd, cwd=path, shell=True, stdout=subprocess.PIPE)
    return pid.stdout.decode('utf-8').strip()


def get_path_head_date(path):
    cmd = 'git log -1 --format="%ci"'
    pid = subprocess.run(cmd, cwd=path, shell=True, stdout=subprocess.PIPE)
    ds = pid.stdout.decode('utf-8').strip()

    # 2021-10-31 00:03:43 -0500
    ts = datetime.datetime.strptime(ds, '%Y-%m-%d %H:%M:%S %z')
    return ts


def get_path_role_name(path):
    metaf = os.path.join(path, 'meta', 'main.yml')
    with open(metaf, 'r') as f:
        meta = yaml.load(f.read())
    return meta['galaxy_info']['role_name']


def get_path_role_namespace(path):
    cmd =  "git remote -v | head -1 | awk '{print $2}'"
    pid = subprocess.run(cmd, cwd=path, shell=True, stdout=subprocess.PIPE)
    origin = pid.stdout.decode('utf-8').strip()
    namespace = origin.replace('https://github.com/', '').split('/')[0]
    return namespace


def get_path_role_version(path):
    ds = get_path_head_date(path)
    version = ds.isoformat().replace('T', '').replace(':', '')
    version = version.split('-')
    version = version[0] + '.' + version[1] + '.' + version[2] + version[3]
    return version


def path_is_role(path):

    paths = glob.glob(f'{path}/*')
    paths = [os.path.basename(x) for x in paths]

    if 'tasks' in paths:
        return True

    if 'library' in paths:
        return True

    if 'handlers' in paths:
        return True

    if 'defaults' in paths:
        return True

    if 'meta' in paths:
        return True

    return False


def make_runtime_yaml(path):
    metadir = os.path.join(path, 'meta')
    runtimef = os.path.join(metadir, 'runtime.yml')

    if not os.path.exists(metadir):
        os.makedirs(metadir)

    data = {'requires_ansible': '>=2.10'}
    #data = {}

    with open(runtimef, 'w') as f:
        yaml.dump(data, f)


def set_path_galaxy_version(path, version):
    gfn = os.path.join(path, 'galaxy.yml')
    with open(gfn, 'r') as f:
        ds = yaml.load(f.read())

    ds['version'] = version
    with open(gfn, 'w') as f:
        yaml.dump(ds, f)
