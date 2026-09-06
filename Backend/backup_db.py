"""Backup the CRM database before reset. Run: .\.venv\Scripts\python.exe backup_db.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from config.settings import DATABASES
import subprocess

db = DATABASES['default']
host = db.get('HOST', 'localhost')
port = db.get('PORT', '3306')
user = db.get('USER', 'root')
password = db.get('PASSWORD', '')
name = db.get('NAME', 'crm_v2')

# Find mysqldump
import shutil
mysqldump = shutil.which('mysqldump')
if not mysqldump:
    # Try common Windows locations
    for candidate in [
        r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe',
        r'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe',
        r'C:\Program Files\MySQL\MySQL Server 9.0\bin\mysqldump.exe',
        r'C:\Program Files\MariaDB 10.6\bin\mysqldump.exe',
        r'C:\ProgramData\MySQL\MySQL Server 8.0\bin\mysqldump.exe',
    ]:
        if os.path.isfile(candidate):
            mysqldump = candidate
            break

if not mysqldump:
    print("ERROR: mysqldump.exe not found.")
    print("Install MySQL or MariaDB, or add mysqldump to your PATH.")
    print("Trying Python-based backup instead...")
    backup_via_python(host, port, user, password, name)
    sys.exit(0)

print(f"Using mysqldump: {mysqldump}")
print(f"Database: {name}@{host}:{port}")

cmd = [
    mysqldump,
    f'-u{user}',
    f'-p{password}',
    f'-h{host}',
    f'-P{port}',
    '--single-transaction',
    '--routines',
    '--triggers',
    name,
]

outfile = os.path.join(os.path.dirname(__file__), 'crm_v2_backup.sql')
with open(outfile, 'w', encoding='utf-8') as f:
    result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

if result.returncode == 0:
    size = os.path.getsize(outfile)
    print(f"Backup saved: {outfile} ({size:,} bytes)")
else:
    print(f"Backup failed: {result.stderr}")
    sys.exit(1)


def backup_via_python(host, port, user, password, name):
    """Fallback: dump all tables via Python + SQL."""
    import sqlalchemy
    engine = sqlalchemy.create_engine(
        f'mysql+pymysql://{user}:{password}@{host}:{port}/{name}'
    )
    with engine.connect() as conn:
        tables = conn.execute(
            sqlalchemy.text("SHOW TABLES")
        ).fetchall()

    outfile = os.path.join(os.path.dirname(__file__), 'crm_v2_backup.sql')
    with open(outfile, 'w', encoding='utf-8') as f:
        f.write(f"-- CRM V2 Backup\n-- Database: {name}\n\n")
        with engine.connect() as conn:
            for (table_name,) in tables:
                f.write(f"-- Table: {table_name}\n")
                f.write(f"DROP TABLE IF EXISTS `{table_name}`;\n")
                create = conn.execute(
                    sqlalchemy.text(f"SHOW CREATE TABLE `{table_name}`")
                ).fetchone()
                f.write(f"{create[1]};\n\n")
                rows = conn.execute(
                    sqlalchemy.text(f"SELECT * FROM `{table_name}`")
                ).fetchall()
                if rows:
                    cols = conn.execute(
                        sqlalchemy.text(f"DESCRIBE `{table_name}`")
                    ).fetchall()
                    col_names = [c[0] for c in cols]
                    f.write(f"INSERT INTO `{table_name}` ({', '.join('`'+c+'`' for c in col_names)}) VALUES\n")
                    for i, row in enumerate(rows):
                        vals = ', '.join(_sql_val(v) for v in row)
                        sep = ',' if i < len(rows) - 1 else ';'
                        f.write(f"  ({vals}){sep}\n")
                    f.write('\n')
    print(f"Python backup saved: {outfile}")


def _sql_val(v):
    if v is None:
        return 'NULL'
    if isinstance(v, bool):
        return '1' if v else '0'
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"
