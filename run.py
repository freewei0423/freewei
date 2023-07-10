#!/usr/bin/env python
# encoding: utf-8
from __future__ import unicode_literals
from __future__ import absolute_import

import os
import os.path
from os import path
import sys
import re
import argparse
from lib import install
from lib import cmd


def show_usage():
    usage = '''
Usage: %s [master_ip|<config_file>.yml]
''' % __file__
    print(usage)


IPADDR_REG_PATTERN = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
IPADDR_REG = re.compile(IPADDR_REG_PATTERN)
def match_ip4addr(string):
    global IPADDR_REG
    return IPADDR_REG.match(string) is not None

def versiontuple(v):
    return tuple(map(int, (v.split("."))))

def version_ge(v1, v2):
    return versiontuple(v1) >= versiontuple(v2)

def check_pip3():
    ret = os.system("pip3 --version >/dev/null 2>&1")
    if ret == 0:
        return
    if install_packages(['python3-pip']) == 0:
        return
    raise Exception("install python3-pip failed")

def check_ansible():
    minimal_ansible_version = '2.9.27'
    cmd.init_ansible_playbook_path()
    ret = os.system("ansible-playbook --version >/dev/null 2>&1")
    if ret == 0:
        ansible_version = os.popen("""ansible-playbook --version | head -1 | grep -oP '[0-9.]+' """).read().strip()
        if version_ge(ansible_version, minimal_ansible_version):
            print("current ansible version: %s. PASS" % ansible_version)
            return
        else:
            print("Current ansible version (%s) is lower than expected(%s). upgrading ... " % (ansible_version, minimal_ansible_version))
    else:
        print("No ansible found. Installing ... ")
    try:
        install_ansible()
    except Exception as e:
        print("Install ansible failed, please try to install ansible manually")
        raise e

def install_packages(pkgs):
    if os.system('grep -Pq "Kylin Linux Advanced Server|CentOS Linux|openEuler" /etc/os-release') == 0:
        return os.system("yum install -y $(yum search pyyaml |grep -iP '^python3\d?-pyyaml\.'| awk '{print $1}') %s" % (" ".join(pkgs)))
    elif os.system('grep -wq "Debian GNU/Linux" /etc/os-release') == 0:
        return os.system("apt install -y %s" % (" ".join(pkgs)))
    else:
        print("Unsupported OS")
        return 255

def install_ansible():
    for pkg in ['python2-pyyaml', 'PyYAML']:
        install_packages([pkg])
    ret = os.system('python3 -m pip install --upgrade pip setuptools wheel')
    if ret != 0:
        raise Exception("Install/updrade pip3 failed. ")
    ret = os.system('python3 -m pip install --upgrade ansible')
    if ret != 0:
        raise Exception("Install ansible failed. ")

def check_passless_ssh(ipaddr):
    cmd = "ssh -o 'StrictHostKeyChecking=no' -o 'PasswordAuthentication=no' root@%s hostname" % (ipaddr)
    ret = os.system(cmd)
    if ret == 0:
        return
    else:
        raise Exception("Passwordless ssh failed, please configure passwordless ssh to root@%s" % (ipaddr))
    try:
        install_passless_ssh(ipaddr)
    except Exception as e:
        print("Configure passwordless ssh failed, please try to configure it manually")
        raise e


def install_passless_ssh(ipaddr):
    rsa_path = os.path.join(os.environ.get("HOME"), ".ssh/id_rsa")
    if not os.path.exists(rsa_path):
        ret = os.system("ssh-keygen -f %s -P '' -N ''" % (rsa_path))
        if ret != 0:
            raise Exception("ssh-keygen")
    print("We are going to run the following command to enable passwordless SSH login:")
    print("")
    print("    ssh-copy-id -i ~/.ssh/id_rsa.pub root@%s" % (ipaddr))
    print("")
    print("Press any key to continue and then input root password to %s" % (ipaddr))
    os.system("read")
    ret = os.system("ssh-copy-id -i ~/.ssh/id_rsa.pub root@%s" % (ipaddr))
    if ret != 0:
        raise Exception("ssh-copy-id")
    ret = os.system("ssh -o 'StrictHostKeyChecking=no' -o 'PasswordAuthentication=no' root@%s hostname" % (ipaddr))
    if ret != 0:
        raise Exception("check passwordless ssh login failed")


def check_env(ipaddr=None):
    check_pip3()
    check_ansible()
    if ipaddr:
        check_passless_ssh(ipaddr)


def random_password(num):
    assert (num >= 6)
    digits = r'23456789'
    letters = r'abcdefghjkmnpqrstuvwxyz'
    uppers = letters.upper()
    punc = r'' # !$@#%^&*-=+?;'
    chars = digits + letters + uppers + punc
    npass = None
    while True:
        npass = ''
        digits_cnt = 0
        letters_cnt = 0
        uppers_cnt = 0
        for i in range(num):
            import random
            ch = random.choice(chars)
            if ch in digits:
                digits_cnt += 1
            elif ch in letters:
                letters_cnt += 1
            elif ch in uppers:
                uppers_cnt += 1
            npass += ch
        if digits_cnt > 1 and letters_cnt > 1 and uppers_cnt > 1:
            return npass
    return npass


conf = """
# # clickhouse_node indicates the node where the clickhouse service needs to be deployed
# clickhouse_node:
#   # IP of the machine to be deployed
#   hostname: 10.127.10.158
#   # SSH Login username of the machine to be deployed
#   user: root
#   # Password of clickhouse
#   ch_password: your-clickhouse-password
# mariadb_node indicates the node where the mariadb service needs to be deployed
mariadb_node:
  # IP of the machine to be deployed
  hostname: 10.127.10.158
  # SSH Login username of the machine to be deployed
  user: root
  # Username of mariadb
  db_user: root
  # Password of mariadb
  db_password: your-sql-password
# primary_master_node indicates the machine running Kubernetes and OneCloud Platform
primary_master_node:
  hostname: 10.127.10.158
  user: root
  # Database connection address
  db_host: 10.127.10.158
  # Database connection username
  db_user: root
  # Database connection password
  db_password: your-sql-password
  # IP of Kubernetes controlplane
  controlplane_host: 10.127.10.158
  # Port of Kubernetes controlplane
  controlplane_port: "6443"
  # OneCloud version
  onecloud_version: 'v3.4.12'
  # OneCloud login username
  onecloud_user: admin
  # OneCloud login user's password
  onecloud_user_password: admin@123
  # This machine serves as a OneCloud private cloud computing node
  as_host: true
  # enable_eip_man for all-in-one mode only
  enable_eip_man: true
  # chose product_version in ['FullStack', 'CMP', 'Edge']
  product_version: 'FullStack'
  image_repository: registry.cn-beijing.aliyuncs.com/yunion
"""

def gen_config(ipaddr):
    global conf
    import os.path
    import yaml
    import os
    config_dir = os.getenv("OCBOOT_CONFIG_DIR")
    image_repository = os.getenv('IMAGE_REPOSITORY')

    cur_path = os.path.abspath(os.path.dirname(__file__))
    if not config_dir:
        config_dir = cur_path
    temp = os.path.join(config_dir, "config-allinone-current.yml")
    verf = os.path.join(cur_path, "VERSION")
    with open(verf, 'r') as f:
        ver = f.read().strip()

    # parameter first; then daily build; at last official build
    if image_repository not in ['', None, 'none'] :
        conf = conf.replace('registry.cn-beijing.aliyuncs.com/yunion', image_repository)
    elif re.search(r'\b\d{8}\.\d$', ver):
        conf = conf.replace('registry.cn-beijing.aliyuncs.com/yunion', 'registry.cn-beijing.aliyuncs.com/yunionio')

    if os.path.exists(temp):
        with open(temp, 'r') as stream:
            try:
                data = (yaml.safe_load(stream))
                if data.get('primary_master_node', {}).get('hostname', '') == ipaddr and \
                   data.get('primary_master_node', {}).get('onecloud_version', '') == ver:
                    print("reuse current yaml: %s" % temp)
                    return temp
            except yaml.YAMLError as exc:
                raise Exception("paring %s error: %s" % (temp, exc))

    mypass_clickhouse = random_password(12)
    mypass_mariadb  = random_password(12)
    with open(temp, 'w') as f:
        f.write(conf.replace('10.127.10.158', ipaddr)
                .replace('your-sql-password', mypass_mariadb)
                .replace('your-clickhouse-password', mypass_clickhouse)
                .replace('v3.4.12', ver))
    return temp


parser = None

def get_args():
    """show argpase snippets"""
    global parser
    parser = argparse.ArgumentParser()
    parser.add_argument('IP_CONF', nargs=1, type=str, help="Input the target IPv4 or Config file")
    parser.add_argument('--offline-data-path', nargs='?', help="offline packages location")
    return parser.parse_args()


def main():
    args = get_args()
    os.chdir(os.path.dirname(os.path.realpath(__file__)))
    ip_conf = str(args.IP_CONF[0])

    # 1. try to get offline data path from optional args
    # 2. if not exist, try to get from os env
    # 3. if got one, save to env for later use.
    offline_data_path = None
    if args.offline_data_path and os.path.isdir(args.offline_data_path):
        offline_data_path = os.path.realpath(args.offline_data_path)
    elif os.environ.get('OFFLINE_DATA_PATH') and os.path.isdir(os.environ.get('OFFLINE_DATA_PATH')):
        offline_data_path = os.path.realpath(os.environ.get('OFFLINE_DATA_PATH'))

    if offline_data_path:
        os.environ['OFFLINE_DATA_PATH'] = offline_data_path
    else:
        os.environ['OFFLINE_DATA_PATH'] = ''
        install_packages(['python3-pip', 'python2-pyyaml', 'PyYAML'])

    if match_ip4addr(ip_conf):
        check_env(ip_conf)
        conf = gen_config(ip_conf)
    elif path.isfile(ip_conf):
        check_env()
        conf = ip_conf
    else:
        print("Wrong args!")
        parser.print_help()
        exit()
    return install.start(conf)


if __name__ == "__main__":
    sys.exit(main())
