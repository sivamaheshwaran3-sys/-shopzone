# PyMySQL-a MySQLdb maadiri use panna (Windows-la mysqlclient install problem varaadhu)
try:
    import pymysql

    pymysql.version_info = (2, 2, 1, "final", 0)
    pymysql.install_as_MySQLdb()
except ImportError:  # SQLite mode-la PyMySQL thevai illa
    pass
