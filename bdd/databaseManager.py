import sqlite3
from tabulate import tabulate
from predefined_queries import PREDEFINED_QUERIES
import csv

class DatabaseManager:
    def __init__(self, db_path='./recipe.db'):
        """
        Initializes the DatabaseManager object.

        :param db_path: Path to the SQLite database file (default is 'bdd.db').
        """
        self.db_path = db_path

    def connect(self):
        """Establish a connection to the database."""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    def get_tables(self):
        """Retrieve the list of tables in the database."""
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return [table[0] for table in self.cursor.fetchall()]

    def get_table_schema(self, table_name):
        """Retrieve the schema for a specific table."""
        self.cursor.execute(f"PRAGMA table_info({table_name});")
        return self.cursor.fetchall()

    def view_table(self, table_name, limit=10):
        """View the first 'limit' rows of a specific table."""
        try:
            self.cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit};")
            rows = self.cursor.fetchall()
            headers = [description[0] for description in self.cursor.description]
            return tabulate(rows, headers=headers, tablefmt="pretty")
        except Exception as e:
            return f"Error viewing table {table_name}: {e}"

    def insert_data(self, table_name, columns, data):
        """Insert a new row into a specific table."""
        try:
            placeholders = ', '.join(['?' for _ in data])
            column_names = ', '.join(columns)
            self.cursor.execute(f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders});", data)
            self.conn.commit()
            return "Data inserted successfully."
        except Exception as e:
            return f"Error inserting data into {table_name}: {e}"

    def insert_bulk_data(self, table_name, columns, data_list):
        """Insert multiple rows into a specific table."""
        try:
            placeholders = ', '.join(['?' for _ in columns])
            column_names = ', '.join(columns)
            self.cursor.executemany(f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders});", data_list)
            self.conn.commit()
            return f"Successfully inserted {len(data_list)} rows into {table_name}."
        except Exception as e:
            return f"Error inserting bulk data into {table_name}: {e}"

    def bulk_insert_from_file(self, table_name, file_path, file_type='csv'):
        """Insert multiple rows into a table from a file (CSV or JSON)."""
        try:
            if file_type.lower() == 'csv':
                with open(file_path, 'r', encoding='utf-8') as file:
                    reader = csv.reader(file)
                    headers = next(reader)  # Extract the first row as headers
                    data = [tuple(row) for row in reader]
            elif file_type.lower() == 'json':
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)  # Assuming the file is a list of dictionaries
                    headers = list(data[0].keys())
                    data = [tuple(item.values()) for item in data]
            else:
                return f"Unsupported file type: {file_type}"

            placeholders = ', '.join(['?' for _ in headers])
            column_names = ', '.join(headers)
            self.cursor.executemany(f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders});", data)
            self.conn.commit()
            return "Bulk data inserted successfully."
        except Exception as e:
            return f"Error bulk inserting data from {file_path} into {table_name}: {e}"

    def update_data(self, table_name, set_clause, where_clause):
        """Update data in a specific table."""
        try:
            self.cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE {where_clause};")
            self.conn.commit()
            return "Data updated successfully."
        except Exception as e:
            return f"Error updating data in {table_name}: {e}"

    def bulk_update_from_file(self, file_path):
        """Update multiple rows in a table from a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                updates = json.load(file)  # Assuming the file is a list of update instructions

            for update in updates:
                table_name = update.get('table_name')
                set_clause = update.get('set_clause')
                where_clause = update.get('where_clause')
                self.update_data(table_name, set_clause, where_clause)

            return "Bulk data updates completed successfully."
        except Exception as e:
            return f"Error bulk updating data from {file_path}: {e}"

    def execute_query(self, query):
        """Run a raw SQL query and return the result."""
        try:
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            headers = [description[0] for description in self.cursor.description]
            return tabulate(rows, headers=headers, tablefmt="pretty")
        except Exception as e:
            return f"Error executing query: {e}"

    def execute_predefined_query(self, query_name, **kwargs):
        """Run a predefined query by name."""
        try:
            query = PREDEFINED_QUERIES.get(query_name)
            if not query:
                return f"No predefined query found with the name '{query_name}'"
            query = query.format(**kwargs)  # Format the query with any passed variables
            return self.execute_query(query)
        except Exception as e:
            return f"Error executing predefined query '{query_name}': {e}"

def Tables(db):
    tables = db.get_tables()
    print("\nTables in the database:")
    print(tabulate([[table] for table in tables], headers=['Table Name'], tablefmt="pretty"))

def TableContent(db, table_name):
    schema = db.get_table_schema(table_name)
    print("\nSchema of table {}: ".format(table_name))
    print(tabulate(schema, headers=['ID', 'Name', 'Type', 'Not Null', 'Default Value', 'Primary Key'], tablefmt="pretty"))

def main():
    db = DatabaseManager()
    db.connect()

    while True:
        print("\nOptions:")
        print("1. View list of tables")
        print("2. View table schema")
        print("3. View table data")
        print("4. Insert single row into table")
        print("5. Insert multiple rows into table")
        print("6. Bulk insert data from file")
        print("7. Update data in table")
        print("8. Bulk update data from file")
        print("9. Execute custom SQL query")
        print("10. Execute predefined query")
        print("11. Exit")

        choice = input("Enter your choice: ")

        if choice == '1':
            Tables(db)

        elif choice == '2':
            Tables(db)
            table_name = input("Enter the table name: ")
            TableContent(db, table_name)

        elif choice == '3':
            Tables(db)
            table_name = input("Enter the table name: ")
            limit = int(input("Enter the number of rows to view (default is 10): ") or 10)
            result = db.view_table(table_name, limit)
            print(result)

        elif choice == '4':
            Tables(db)
            table_name = input("Enter the table name: ")
            TableContent(db, table_name)
            columns = input("Enter the columns to insert into (comma-separated): ").split(',')
            data = input("Enter the data to insert (comma-separated values): ").split(',')
            result = db.insert_data(table_name, columns, data)
            print(result)

        elif choice == '5':
            Tables(db)
            table_name = input("Enter the table name: ")
            TableContent(db, table_name)
            columns = input("Enter the columns to insert into (comma-separated): ").split(',')
            num_rows = int(input("Enter the number of rows to insert (default is 1000): ") or 1000)
            data_list = []
            for i in range(num_rows):
                data = input(f"Enter the data for row {i+1} (comma-separated) (p=pass, b=break): ")
                if data == 'p':
                    continue
                if data == 'b':
                    break
                data = data.split(',')
                data_list.append(data)
            result = db.insert_bulk_data(table_name, columns, data_list)
            print(result)

        elif choice == '6':
            Tables(db)
            table_name = input("Enter the table name: ")
            file_path = input("Enter the path to the file (CSV or JSON): ")
            file_type = input("Enter the file type (csv or json): ")
            print(db.bulk_insert_from_file(table_name, file_path, file_type))
        elif choice == '7':
            Tables(db)
            table_name = input("Enter the table name: ")
            set_clause = input("Enter the SET clause (e.g., 'column1=value1, column2=value2'): ")
            where_clause = input("Enter the WHERE clause (e.g., 'id=1'): ")
            result = db.update_data(table_name, set_clause, where_clause)
            print(result)

        elif choice == '8':
            file_path = input("Enter the path to the JSON file for updates: ")
            print(db.bulk_update_from_file(file_path))
        elif choice == '9':
            query = input("Enter your SQL query: ")
            result = db.execute_query(query)
            print(result)

        elif choice == '10':
            print(f"Available predefined queries: {list(PREDEFINED_QUERIES.keys())}")
            query_name = input("Enter the predefined query name: ")
            result = db.execute_predefined_query(query_name)
            print(result)


        elif choice == '11':
            print("Exiting...")
            break

        else:
            print("Invalid choice. Please try again.")

    db.close()

# todo add predefined query
#select t.id, t.name, c.id, c.name from tag as t left join category as c on t.category_id == c.id
if __name__ == "__main__":
    main()
