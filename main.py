import sqlite3
import os
import argparse
from biplist import *
import plistlib

def listApp(conn):
    sql = '''
SELECT 
    domain 
FROM 
    Files
WHERE
	domain LIKE 'APPDomain-%'
GROUP BY 
    domain;'''

    c = conn.cursor()
    for row in c.execute(sql):
        domain = row[0][len('AppDomain-'):]
        print(domain)

def listDomain(conn):
    sql = '''
SELECT 
    domain 
FROM 
    Files
GROUP BY 
    domain;'''

    c = conn.cursor()
    for row in c.execute(sql):
        domain = row[0]
        print(domain)

def modifyInfoPlist(backup, app):
    infoPlistPath = os.path.join(backup, 'Info.plist')
    try:
        with open(infoPlistPath, 'rb') as f:
            plist = plistlib.load(f)
        
        # 从 Applications 中删除包含 app 的记录
        if 'Applications' in plist:
            plist['Applications'] = {k: v for k, v in plist['Applications'].items() if app not in k}
        
        # 从 Installed Applications 数组中删除包含 app 的记录
        if 'Installed Applications' in plist:
            plist['Installed Applications'] = [item for item in plist['Installed Applications'] if app not in item]
        
        # 将修改后的内容写回源文件
        with open(infoPlistPath, 'wb') as f:
            plistlib.dump(plist, f)
        
        print(f"已成功从 Info.plist 中删除 {app} 相关记录")
    except Exception as e:
        print(f"修改 Info.plist 时出错：{str(e)}")

def modifyManifestlist(backup, app):
    infoPlistPath = os.path.join(backup, 'Manifest.plist')
    try:
        with open(infoPlistPath, 'rb') as f:
            plist = plistlib.load(f)
        
        # 从 Applications 中删除包含 app 的记录
        if 'Applications' in plist:
            plist['Applications'] = {k: v for k, v in plist['Applications'].items() if app not in k}

        # 将修改后的内容写回源文件
        with open(infoPlistPath, 'wb') as f:
            plistlib.dump(plist, f)
        
        print(f"已成功从 Manifest.plist 中删除 {app} 相关记录")
    except Exception as e:
        print(f"修改 Manifest.plist 时出错：{str(e)}")


def deleteApp(backup, conn, app):
    sql = f"""
SELECT 
    fileID, relativePath, flags 
FROM 
    Files
WHERE
	domain LIKE '%{app}%'
    """
    c = conn.cursor()
    for row in c.execute(sql):
        fileID = row[0]
        src = os.path.join(backup, fileID[:2], fileID)
        if os.path.exists(src):
            os.remove(src)


    modifyInfoPlist(backup=backup, app=app)
    modifyManifestlist(backup=backup, app=app)

    sql = f"""
DELETE FROM Files
WHERE
	domain LIKE '%{app}%'
    """
    c.execute(sql)
    conn.commit()

def deleteDomain(backup, conn, domain):
    sql = f"""
SELECT 
    fileID, relativePath, flags 
FROM 
    Files
WHERE
	domain='{domain}'
    """
    c = conn.cursor()
    for row in c.execute(sql):
        fileID = row[0]
        src = os.path.join(backup, fileID[:2], fileID)
        if os.path.exists(src):
            os.remove(src)

    sql = f"""
DELETE FROM Files
WHERE
	domain='{domain}'
    """
    c.execute(sql)
    conn.commit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='ibackup_trim')
    parser.add_argument('--backup', help='备份文件目录', required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list-app', action='store_true', help='列出App')
    group.add_argument('--list-domain', action='store_true', help='列出Domain')
    group.add_argument('--delete-app', help='删除指定app')
    group.add_argument('--delete-domain', help='删除指定Domain')
    args = parser.parse_args()
    
    conn = sqlite3.connect(os.path.join(args.backup, 'Manifest.db'))
    if args.list_app:
        listApp(conn=conn)
    elif args.list_domain:
        listDomain(conn=conn)
    elif args.delete_app:
        if 'apple' in args.delete_app.lower():
            print("跳过删除包含'apple'的应用")
        else:
            deleteApp(backup=args.backup, conn=conn, app=args.delete_app)
    elif args.delete_domain:
        if 'appdomain' in args.delete_domain.lower():
            app = args.delete_domain.split('-')[1].replace('group.', '')
            print("请使用 --delete-app '%s'" % app)
        elif 'apple' in args.delete_domain.lower():
            print("跳过删除包含'apple'的Domain")
        else:
            deleteDomain(backup=args.backup, conn=conn, domain=args.delete_domain)
    
    # 关闭WAL模式
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.commit()

    conn.close()
