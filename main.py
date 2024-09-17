import sqlite3
import os
import argparse
import shutil
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

def shadow(backup, out):
    # 获取backup目录的最后一级名称
    backup_name = os.path.basename(os.path.normpath(backup))
    
    # 将out目录与backup最后一级名称结合
    out = os.path.join(out, backup_name)

    # 确保输出目录存在
    os.makedirs(out, exist_ok=True)

    # 将backup和out转换为绝对路径
    backup = os.path.abspath(backup)
    out = os.path.abspath(out)

    # 遍历backup目录中的所有文件和子目录
    for root, dirs, files in os.walk(backup):
        for file in files:
            # 获取源文件的完整路径
            src_path = os.path.abspath(os.path.join(root, file))
            # 计算相对路径
            rel_path = os.path.relpath(src_path, backup)
            # 构建目标路径
            dst_path = os.path.abspath(os.path.join(out, rel_path))

            # 确保目标目录存在
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)

            # 检查文件名是否为特殊文件
            special_files = ['Info.plist', 'Manifest.db', 'Manifest.plist', 'Status.plist']
            if file in special_files:
                # 对于特殊文件，复制而不是创建软链接
                shutil.copy2(src_path, dst_path)
            else:
                # 创建软链接
                try:
                    os.symlink(src_path, dst_path)
                except FileExistsError:
                    # 如果目标已存在，则先删除再创建软链接
                    os.remove(dst_path)
                    os.symlink(src_path, dst_path)

    print(f"已在 {out} 目录中创建 {backup} 目录的软链接和复制特殊文件")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='ibackup_trim')
    parser.add_argument('--backup', help='备份文件目录', required=True)
    parser.add_argument('--out', help='输出目录')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--shadow', action='store_true', help='启用影子模式')
    group.add_argument('--list-app', action='store_true', help='列出App')
    group.add_argument('--list-domain', action='store_true', help='列出Domain')
    group.add_argument('--delete-app', help='删除指定app')
    group.add_argument('--delete-domain', help='删除指定Domain')
    args = parser.parse_args()
    
    if args.shadow:
        if not args.out:
            parser.error("使用 --shadow 时必须指定 --out 参数")
        else:
            shadow(backup=args.backup, out=args.out)
            exit(0)
    
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
