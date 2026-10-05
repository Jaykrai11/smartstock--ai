import pathlib, re

import duckdb

sql = pathlib.Path(__file__).with_name("analysis.sql").read_text()
con = duckdb.connect()
for block in re.split(r"-- name: ", sql)[1:]:
    name, body = block.split("\n", 1)
    print(f"\n=== {name} ==="); print(con.sql(body.strip().rstrip(";")).df().to_string(index=False))
