# ibackup_trim

#### 创建备份文件

```bash
idevicebackup2 backup --full -u <udid> <backup_path>
```

#### 创建影子数据
* 会在`out`目录下创建对应的软链
```bash
python main.py --shadow --backup <backup_path> --out <out_path>
```
* 后续操作中的 `backup` 路径均为影子数据路径

#### 列出App

```bash
python main.py --list-app --backup <backup_path>
```

#### 删除App

```bash
python main.py --delete-app --backup <backup_path> --app <app_name>
```

#### 列出Domain

```bash
python main.py --list-domain --backup <backup_path>
```

#### 删除Domain

```bash
python main.py --delete-domain --backup <backup_path> --domain <domain_name>
```

#### 恢复备份

```bash
idevicebackup2 restore --system --remove -d <shadow_path>
```