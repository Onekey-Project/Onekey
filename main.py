import os
import vdf
import time
import winreg
import requests
import traceback
import subprocess
import ujson as json
from pathlib import Path
from multiprocessing.pool import ThreadPool
from multiprocessing.dummy import Pool, Lock

requests.packages.urllib3.disable_warnings()

lock = Lock()

print('\033[1;32;40m _____   __   _   _____   _   _    _____  __    __\033[0m')
print('\033[1;32;40m/  _  \ |  \ | | | ____| | | / /  | ____| \ \  / /\033[0m')
print('\033[1;32;40m| | | | |   \| | | |__   | |/ /   | |__    \ \/ /\033[0m')
print('\033[1;32;40m| | | | | |\   | |  __|  | |\ \   |  __|    \  /\033[0m')
print('\033[1;32;40m| |_| | | | \  | | |___  | | \ \  | |___    / /\033[0m')
print('\033[1;32;40m\_____/ |_|  \_| |_____| |_|  \_\ |_____|  /_/\033[0m')
print('\033[1;32;40m作者ikun\033[0m')
print('\033[1;32;40m当前版本13.2\033[0m')
print('\033[1;31;40m前有沧海颐粟（胡峰）倒卖，后有985某硕（王亮）以Onekey的名义二改，你俩真是有实力的！\033[0m')
print('\033[1;32;40m温馨提示：App ID可以在Steam商店页面或SteamDB找到\033[0m')

default = {'token': ''}

def gen_config():
    with open("./config.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(default, indent=2, ensure_ascii=False,
                escape_forward_slashes=False))
        f.close()
        if (not os.getenv('build')):
            print('\033[1;32;40m首次启动或配置文件被删除，已创建默认配置文件\033[0m')
            print(f'\033[1;32;40m\n建议您到.{os.path.sep}config.json修改配置后重新打开Onekey\033[0m')
        return default
    
def load_config():
    if os.path.exists('config.json'):
        with open('./config.json', 'r', encoding="utf-8") as config_file:
            config = json.load(config_file)
    else:
        gen_config()
        with open('./config.json', 'r', encoding="utf-8") as config_file:
            config = json.load(config_file)
    return config

config = load_config()
token = config.get('token','')


def get(branch, path):
    url_list = [f'https://raw.githubusercontent.com/{repo}/{branch}/{path}',
                f'https://github.moeyy.xyz/raw.githubusercontent.com/{repo}/{branch}/{path}',
                f'https://mirror.ghproxy.com/raw.githubusercontent.com/{repo}/{branch}/{path}']
    retry = 3
    while True:
        for url in url_list:
            try:
                r = requests.get(url,verify=False)
                if r.status_code == 200:
                    return r.content
            except requests.exceptions.ConnectionError:
                print(f"\033[33m清单获取失败:{path}\033[0m")
                retry -= 1
                if not retry:
                    print(f"\033[33m超过最大重试次数，请检查网络\033[0m")
                    raise

def get_manifest(branch, path, steam_path: Path):
    try:
        if path.endswith('.manifest'):
            depot_cache_path = steam_path / 'depotcache'
            with lock:
                if not depot_cache_path.exists():
                    depot_cache_path.mkdir(exist_ok=True)
            save_path = depot_cache_path / path
            if save_path.exists():
                with lock:
                    print(f"\033[33m已存在清单: {path}\033[0m")
                return
            content = get(branch, path)
            with lock:
                print(f'\033[1;32;40m清单下载成功: {path}\033[0m')
            with save_path.open('wb') as f:
                f.write(content)
        elif path == 'Key.vdf':
            content = get(branch, path)
            with lock:
                print(f'\033[1;32;40m密钥文件下载成功: {path}\033[0m')
            depots_config = vdf.loads(content.decode(encoding='utf-8'))
            if depotkey_merge(steam_path / 'config' / path, depots_config):
                print(f'\033[1;32;40m合并密钥：{path}\033[0m')
            if stool_add([(depot_id, '1', depots_config['depots'][depot_id]['DecryptionKey'])
                     for depot_id in depots_config['depots']]):
                print('\033[1;32;40m导入SteamTools成功\033[0m')
    except KeyboardInterrupt:
        raise
    except:
        traceback.print_exc()
        raise
    return True


def depotkey_merge(config_path, depots_config):
    if not config_path.exists():
        with lock:
            print('密钥文件不存在')
        return
    with open(config_path, encoding='utf-8') as f:
        config = vdf.load(f)
    software = config['InstallConfigStore']['Software']
    valve = software.get('Valve') or software.get('valve')
    steam = valve.get('Steam') or valve.get('steam')
    if 'depots' not in steam:
        steam['depots'] = {}
    steam['depots'].update(depots_config['depots'])
    with open(config_path, 'w', encoding='utf-8') as f:
        vdf.dump(config, f, pretty=True)
    return True

def stool_add(depot_list):
    steam_path = get_steam_path()
    for depot_id, type_, depot_key in depot_list:
        lua_content = f'addappid({depot_id}, {type_}, "{depot_key}")'
    lua_filename = f"OP_{depot_id}.lua"
    lua_filepath = steam_path / "config" / "stplug-in" / lua_filename
    with open(lua_filepath, "w", encoding="utf-8") as lua_file:
        lua_file.write(lua_content)
    luapacka_path = steam_path / "config" / "stplug-in" / "luapacka.exe"
    subprocess.run([str(luapacka_path), str(lua_filepath)])
    os.remove(lua_filepath)
    return True

def get_steam_path():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam')
    steam_path = Path(winreg.QueryValueEx(key, 'SteamPath')[0])
    return steam_path

steam_path = get_steam_path()
print(f'\033[1;32;40m当前Steam路径:{steam_path}\033[0m')

def main(app_id):
    header = {'Authorization':f'{token}'}
    repo_url = f'https://api.github.com/repos/{repo}/branches/{app_id}'
    r_repo = requests.get(repo_url,headers=header,verify=False)
    if 'commit' in r_repo.json():
        branch = r_repo.json()['name']
        path_url = r_repo.json()['commit']['commit']['tree']['url']
        date = r_repo.json()['commit']['commit']['author']['date']
        r_path = requests.get(path_url,headers=header,verify=False)
        if 'tree' in r_path.json():
            stool_add([(app_id, '1', None)])
            result_list = []
            with Pool(32) as pool:
                pool: ThreadPool
                for i in r_path.json()['tree']:
                    result_list.append(pool.apply_async(get_manifest, (branch, i['path'], get_steam_path())))
                try:
                    while pool._state == 'RUN':
                        if all([result.ready() for result in result_list]):
                            break
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    with lock:
                        pool.terminate()
                    raise
            if all([result.successful() for result in result_list]):
                print(f'\033[1;32;40m当前清单仓库清单最新更新时间:{date}\033[0m')
                print(f'\033[1;32;40m此游戏清单下载+解锁成功，App ID:{app_id}\033[0m')
                print('\033[1;32;40m通过SteamTools重启Steam即可生效\033[0m')
                os.system('pause')
                return True
    print(f'\033[31m入库失败: {app_id}\033[0m')
    os.system('pause')
    return False

repo = 'Onekey-Project/OnekeyPro'

if __name__ == '__main__':
    main(input('需要入库的App ID: '))