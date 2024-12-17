
import oracledb

# Enable Thick mode with the correct library path
oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient_arm/instantclient_23_3")

# Oracle connection details
username = 'admin'
password = 'Oraclegautam2468@'
dsn = "tcps://adb.ap-hyderabad-1.oraclecloud.com:1522/ge754cdabed3f17_gautamdb_tpurgent.adb.oraclecloud.com?wallet_location=/opt/oracle_wallet&retry_count=20&retry_delay=3"

def get_db_connection():
    try:
        connection = oracledb.connect(user=username, password=password, dsn=dsn)
        return connection
    except oracledb.Error as e:
        print(f"Error: {e}")
        return None