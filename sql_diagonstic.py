# Database Connection Diagnostic Tool
# Add this to a new file or run as a standalone script to diagnose connection issues

import os
import sys
import time
import socket
import pyodbc
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Get connection parameters from environment variables
server = os.getenv("SERVER", "localhost")
database = os.getenv("DATABASE", "ReportServer")
username = os.getenv("USERNAME", "")
password = os.getenv("PASSWORD", "")

def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "="))
    print("=" * 50)

def test_network_connectivity():
    """Test basic network connectivity to the SQL Server"""
    print_section("NETWORK CONNECTIVITY TEST")
    
    try:
        # Extract server name and port (default is 1433 for SQL Server)
        parts = server.split(',')
        hostname = parts[0]
        port = int(parts[1]) if len(parts) > 1 else 1433
        
        print(f"Testing connectivity to {hostname} on port {port}...")
        
        # Simple socket connection test
        start_time = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)  # 10 second timeout for socket connection
        
        try:
            s.connect((hostname, port))
            connected = True
        except Exception as e:
            connected = False
            print(f"Socket connection error: {e}")
        finally:
            s.close()
        
        end_time = time.time()
        
        if connected:
            print(f"✅ Successfully connected to {hostname}:{port} in {end_time - start_time:.2f} seconds")
        else:
            print(f"❌ Failed to connect to {hostname}:{port}")
            print("\nPossible issues:")
            print("  - SQL Server name is incorrect")
            print("  - SQL Server is not running")
            print("  - Firewall is blocking connection")
            print("  - Network restrictions in corporate environment")
    
    except Exception as e:
        print(f"Network test failed: {e}")

def list_available_drivers():
    """List all available ODBC drivers"""
    print_section("AVAILABLE ODBC DRIVERS")
    
    try:
        drivers = pyodbc.drivers()
        if drivers:
            print("Available ODBC drivers:")
            for i, driver in enumerate(drivers, 1):
                print(f"{i}. {driver}")
                
            # Check if the SQL Server driver is available
            sql_server_drivers = [d for d in drivers if 'SQL Server' in d]
            if sql_server_drivers:
                print("\n✅ SQL Server drivers found:")
                for driver in sql_server_drivers:
                    print(f"  - {driver}")
            else:
                print("\n❌ No SQL Server drivers found!")
                print("Please install the Microsoft ODBC Driver for SQL Server")
        else:
            print("No ODBC drivers found on this system")
    except Exception as e:
        print(f"Failed to list drivers: {e}")

def test_odbc_connection(timeout=60):
    """Test ODBC connection with different methods"""
    print_section("ODBC CONNECTION TEST")
    
    # Method 1: Using trusted connection (Windows authentication)
    print("Method 1: Testing with Windows Authentication...")
    try:
        conn_string = (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'Trusted_Connection=yes;'
            f'timeout={timeout}'
        )
        
        start_time = time.time()
        print(f"Connecting with timeout: {timeout} seconds...")
        conn = pyodbc.connect(conn_string)
        end_time = time.time()
        
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        
        print(f"✅ Windows Auth connection successful in {end_time - start_time:.2f} seconds!")
        print(f"SQL Server Version: {version[:50]}...")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Windows Auth connection failed: {e}")
    
    # Only try SQL authentication if username and password are provided
    if username and password:
        print("\nMethod 2: Testing with SQL Server Authentication...")
        try:
            conn_string = (
                f'DRIVER={{ODBC Driver 17 for SQL Server}};'
                f'SERVER={server};'
                f'DATABASE={database};'
                f'UID={username};'
                f'PWD={password};'
                f'timeout={timeout}'
            )
            
            start_time = time.time()
            print(f"Connecting with timeout: {timeout} seconds...")
            conn = pyodbc.connect(conn_string)
            end_time = time.time()
            
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            
            print(f"✅ SQL Auth connection successful in {end_time - start_time:.2f} seconds!")
            print(f"SQL Server Version: {version[:50]}...")
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"❌ SQL Auth connection failed: {e}")
    else:
        print("\nSkipping SQL Server Authentication test (username/password not provided)")

def test_query_execution():
    """Test if we can execute a simple query"""
    print_section("QUERY EXECUTION TEST")
    
    try:
        # Try different connection methods
        connection_methods = [
            {
                "name": "Windows Authentication",
                "conn_string": f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;timeout=60'
            }
        ]
        
        if username and password:
            connection_methods.append({
                "name": "SQL Authentication",
                "conn_string": f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};timeout=60'
            })
        
        for method in connection_methods:
            print(f"Testing with {method['name']}...")
            try:
                conn = pyodbc.connect(method['conn_string'])
                cursor = conn.cursor()
                
                print("Executing simple test query...")
                cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES")
                count = cursor.fetchone()[0]
                
                print(f"✅ Query executed successfully! Found {count} tables.")
                
                # Try to query the ExecutionLog3 table specifically
                print("\nTesting access to ExecutionLog3 table...")
                try:
                    cursor.execute("SELECT TOP 1 * FROM ExecutionLog3")
                    print("✅ Successfully queried ExecutionLog3 table")
                except Exception as e:
                    print(f"❌ Failed to query ExecutionLog3 table: {e}")
                    print("This might indicate a permissions issue or the table doesn't exist")
                
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"❌ Query execution failed with {method['name']}: {e}")
    except Exception as e:
        print(f"Query test failed: {e}")

def print_connection_summary():
    """Print a summary of connection information and common solutions"""
    print_section("CONNECTION TROUBLESHOOTING SUMMARY")
    
    print("Connection details:")
    print(f"  Server: {server}")
    print(f"  Database: {database}")
    print(f"  Using Windows Auth: {'No' if username and password else 'Yes'}")
    
    print("\nCommon solutions for connection timeout issues in corporate environments:")
    print("1. Network/Firewall Issues:")
    print("   - Ensure SQL Server port (usually 1433) is open on the server firewall")
    print("   - Check corporate VPN connectivity if connecting remotely")
    print("   - Verify there are no network policies blocking SQL Server access")
    
    print("\n2. Authentication Issues:")
    print("   - Ensure your account has proper permissions to access the database")
    print("   - In a corporate environment, Windows Authentication may be required")
    print("   - SQL credentials might be disabled at the server level")
    
    print("\n3. SQL Server Configuration:")
    print("   - Verify SQL Server is configured to allow remote connections")
    print("   - Check if TCP/IP protocol is enabled in SQL Server Configuration Manager")
    print("   - Ensure the SQL Server Browser service is running (for named instances)")
    
    print("\n4. Environment Restrictions:")
    print("   - Some corporate environments restrict direct database access")
    print("   - Consider asking IT if they have API endpoints instead of direct DB access")
    print("   - Check if you need to be on a specific corporate network segment")

if __name__ == "__main__":
    print("SQL Server Connection Diagnostic Tool")
    print(f"Python version: {sys.version}")
    
    list_available_drivers()
    test_network_connectivity()
    test_odbc_connection()
    test_query_execution()
    print_connection_summary()