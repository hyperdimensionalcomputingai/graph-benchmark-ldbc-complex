from pathlib import Path

import ladybug as lb


def setup_db(db_name: str, overwrite: bool = True) -> lb.Connection:
    """
    Create a new Kuzu database and a graph schema based on DDL commands.
    """
    if overwrite:
        Path(db_name).unlink(missing_ok=True)
    db = lb.Database(db_name)
    conn = lb.Connection(db)

    with open("./etl/schema.cypher", "r") as f:
        schema_ddl = f.read()
    assert schema_ddl.startswith("CREATE")
    conn.execute(schema_ddl)
    print("Schema created successfully.")
    return conn


def ingest_data(conn: lb.Connection, data_path: str):
    """
    Ingest data from the given path into the existing database.
    """
    with open("./etl/copy.cypher", "r") as f:
        copy_ddl = f.read()
    assert copy_ddl.startswith("COPY")
    conn.execute(copy_ddl)
    print("Data ingested successfully.")


# (node table, property) pairs with selective equality/range filters in
# ladybugdb/query.py. ART indexes serve both `=` and range (`>`) scans,
# analogous to the BTREE scalar indexes in lance_graph/build_graph.py.
# CONTAINS predicates (Forum.title, Post.content, ...) cannot use ART
# indexes and are deliberately omitted; ID columns already have PK HASH
# indexes and need no secondary index.
SECONDARY_INDEXES: list[tuple[str, str]] = [
    ("Place", "name"),  # Q1, Q9, Q12, Q16, Q24, Q27, Q28: pl.name = ...
    ("Tag", "name"),  # Q1, Q7, Q10, Q18, Q23, Q24, Q26, Q27: t.name = ...
    # Creating secondary index on small tables slows things down
    # ("Organisation", "name"),  # Q6, Q15, Q17, Q18, Q22, Q25: o.name = ...
    # ("Tagclass", "name"),  # Q14, Q28: tc.name = ...
    ("Person", "firstName"),  # Q2, Q13, Q25, Q29: p.firstName = ...
    ("Person", "lastName"),  # Q9, Q23 (+ Q4, Q13, Q25, Q29): p.lastName = ...
    ("Person", "birthday"),  # Q8: p.birthday > DATE(...)
    ("Comment", "length"),  # Q4, Q20: c.length > ...
]


def create_secondary_indexes(conn: lb.Connection):
    """
    Create ART secondary indexes after bulk ingest (building them on an
    empty table before COPY would slow down the load).
    """
    for table, prop in SECONDARY_INDEXES:
        idx_name = f"{table}_{prop}_art"
        conn.execute(
            f"CREATE ART INDEX {idx_name} FOR (n:{table}) ON (n.{prop})"
        )
        print(f"Created ART index: {idx_name} ON {table}({prop})")


if __name__ == "__main__":
    DB_NAME = "ldbc_snb_sf1.lbdb"
    DATA_PATH = "../csv"
    conn = setup_db(DB_NAME, overwrite=True)
    ingest_data(conn, DATA_PATH)
    create_secondary_indexes(conn)
