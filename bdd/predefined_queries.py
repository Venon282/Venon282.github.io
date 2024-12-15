PREDEFINED_QUERIES = {
    'list_tags_with_categories': """
        SELECT t.id, t.name, c.id, c.name
        FROM tag AS t
        LEFT JOIN category AS c
        ON t.category_id = c.id
        ORDER BY c.name, t.name;
    """,
    'count_rows_in_table': """
        SELECT '{table_name}' AS table_name, COUNT(*) AS total_rows
        FROM {table_name};
    """
}
