# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import getopt
import os
import shutil
import sys
import zipfile

from requests import session
import json


def getdefault(mcversion, forgeversion, packversion, modpackname, modpackauthor):
    defaultjson = \
        {
            'minecraft':
                {
                    'version': mcversion,
                    'modLoaders': [
                        {
                            'id': 'forge-' + forgeversion,
                            'primary': True
                        }
                    ]
                },
            'manifestType': 'minecraftModpack',
            'manifestVersion': 1,
            'name': modpackname,
            'version': packversion,
            'author': modpackauthor,
            'files': [],
            "overrides": "overrides"

        }
    return defaultjson


def computeHash(data):
    binput = bytearray()
    for byte in data:
        if not (byte == 9 or byte == 10 or byte == 13 or byte == 32):
            binput.append(byte)

    return mmHash(binput)


def mmHash(data: bytes):
    m = 0x5bd1e995
    r = 24
    intmax = pow(2, 32)
    seed = 1
    length = len(data) % intmax
    if length == 0:
        return 0
    h = seed ^ length
    i = 0
    while length >= 4:
        k = data[i] | data[i + 1] << 8 | data[i + 2] << 16 | data[i + 3] << 24

        k *= m
        k %= intmax
        k ^= k >> r
        k *= m
        k %= intmax

        h *= m
        h %= intmax
        h ^= k

        i += 4
        length -= 4

    if length == 3:
        h ^= (data[i] | data[i + 1] << 8 | data[i + 2] << 16)
        h *= m
    elif length == 2:
        h ^= (data[i] | data[i + 1] << 8)
        h *= m
    elif length == 1:
        h ^= data[i]
        h *= m

    h %= intmax
    h ^= h >> 13
    h *= m
    h %= intmax
    h ^= h >> 15
    return h


def ignore_files(dir, names):
    ignore_list = ['screenshots', 'saves', 'local', 'logs', 'fonts', 'crash-reports', 'caches', 'cache', '.mixin.out', 'usercache.json', 'usernamecache.json', 'mods']
    alist = []
    for name in names:
        if name in ignore_list:
            alist.append(name)
    return alist


def main(argv):
    if len(argv) < 1:
        print('tocfpack.py -k [APIkey] -d [.minecraft directory] -m [mc version] -f [forge version] -v [pack version] '
              '-n [pack name] -a [author(s)]')
        sys.exit(2)

    apikey = ''
    folder = '.'
    mcver = '1.12.2'
    forgever = '14.23.5.2860'
    packver = '1.0'
    packname = 'defaultpacl'
    packauthor = 'defaultauthor'
    help = 'tocfpack.py -k [APIkey] -d [.minecraft directory] -m [mc version] -f [forge version] -v [pack version] -n ' \
           '[pack name] -a [author(s)] '
    try:
        opts, args = getopt.getopt(argv, "hk:d:m:f:v:n:a:")
    except getopt.GetoptError:
        print(help)
        sys.exit(2)
    for opt, arg in opts:
        if opt in ['-h']:
            print(help)
            sys.exit(0)
        if opt in ['-k']:
            apikey = arg
        if opt in ['-d']:
            folder = arg
        if opt in ['-m']:
            mcver = arg
        if opt in ['-f']:
            forgever = arg
        if opt in ['-v']:
            packver = arg
        if opt in ['-n']:
            packname = arg
        if opt in ['-a']:
            packauthor = arg

    if apikey == '':
        print('Please pass your api key')
        sys.exit(2)
    print(apikey)
    url = 'https://api.curseforge.com/v1/fingerprints'
    web = session()
    default = getdefault(mcver, forgever, packver, packname, packauthor)
    noncflist = []
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'x-api-key': apikey}
    for f in os.listdir(folder + '/mods'):
        if f.endswith('.jar') or f.endswith('.zip'):
            fullpath = os.path.join(folder + '/mods', f)
            print(fullpath)
            file = open(fullpath, 'rb')
            fingerprint = computeHash(file.read())
            file.close()
            response = web.post(url, json={"fingerprints": [fingerprint]}, headers=headers)
            if response.status_code == 200:
                resp_json = response.json(strict=False)
                if len(resp_json['data']['exactMatches']) > 0:
                    modid = resp_json['data']['exactMatches'][0]['file']['modId']
                    fileid = resp_json['data']['exactMatches'][0]['file']['id']
                    default['files'].append({
                        "projectID": modid,
                        "fileID": fileid,
                        "required": True
                    })
                else:
                    noncflist.append(fullpath)
    os.makedirs(packname, exist_ok=True)
    manifest = open(packname + '/manifest.json', "w")
    manifest.write(json.dumps(default, indent=4))
    manifest.close()
    os.makedirs(packname + '/overrides', exist_ok=True)
    os.makedirs(packname + '/overrides/mods', exist_ok=True)
    for m in noncflist:
        shutil.copy(m, packname + '/overrides/mods/')
    shutil.copytree(folder, packname + '/overrides/', dirs_exist_ok=True, ignore=ignore_files)

    with zipfile.ZipFile(packname + '-' + packver + '.zip', mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
        for dir, subdirs, files in os.walk(packname + '/overrides'):
            for f in files:
                fp = os.path.join(dir, f)
                zf.write(fp, fp.replace(packname, ''))
            for d in subdirs:
                dp = os.path.join(dir, d)
                zf.write(dp, dp.replace(packname, ''))
        zf.write(packname + '/manifest.json', 'manifest.json')

    shutil.rmtree(packname, ignore_errors=True)

if __name__ == "__main__":
    main(sys.argv[1:])
