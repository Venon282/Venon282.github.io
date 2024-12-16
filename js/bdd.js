class Database {
    constructor(databaseUrl) {
      this.databaseUrl = databaseUrl;
      this.db = null;
    }

    // Initialize the database by fetching it from the URL and loading it into sql.js
    async initialize() {
      const response = await fetch(this.databaseUrl);
      const arrayBuffer = await response.arrayBuffer();
      const SQL = await initSqlJs({
        locateFile: file => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.12.0/${file}`
      });

      this.db = new SQL.Database(new Uint8Array(arrayBuffer));
    }

    // Execute a query and return the result
    exec(query, params = []) {
      if (!this.db) {
        throw new Error("Database not initialized.");
      }

      const statement = this.db.prepare(query);

      // Bind parameters if provided
      if (params.length > 0) {
        statement.bind(params);
      }

      let result = statement.step();
      const rows = [];

      // Collect the result
      while (result) {
        rows.push(statement.getAsObject());
        result = statement.step();
      }

      statement.free();
      return rows;
    }

    // Insert a record into a table
    insert(table, columns, values) {
      const columnNames = columns.join(", ");
      const placeholders = columns.map(() => "?").join(", ");
      const query = `INSERT INTO ${table} (${columnNames}) VALUES (${placeholders})`;

      this.exec(query, values);
    }

    // Update a record in a table
    update(table, columns, values, condition) {
      const setClause = columns.map(col => `${col} = ?`).join(", ");
      const query = `UPDATE ${table} SET ${setClause} WHERE ${condition}`;

      this.exec(query, values);
    }

    // Delete a record from a table
    delete(table, condition) {
      const query = `DELETE FROM ${table} WHERE ${condition}`;
      this.exec(query);
    }

    // Select records from a table
    select(table, columns = "*", condition = "1=1", limit = 10) {
      const query = `SELECT ${columns} FROM ${table} WHERE ${condition} LIMIT ${limit}`;
      return this.exec(query);
    }

    // Check if a table exists in the database
    tableExists(tableName) {
      const query = `SELECT name FROM sqlite_master WHERE type='table' AND name='${tableName}'`;
      const result = this.exec(query);
      return result.length > 0;
    }

    // Get all the rows from a table
    getAllRows(table) {
      return this.select(table);
    }
  }


export default Database
