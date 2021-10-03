import os

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from .. import read_sql


@pytest.fixture(scope="module")  # type: ignore
def mysql_url() -> str:
    conn = os.environ["MYSQL_URL"]
    return conn


def test_mysql_without_partition(mysql_url: str) -> None:
    query = "select * from test_table limit 3"
    df = read_sql(mysql_url, query)
    expected = pd.DataFrame(
        index=range(3),
        data={
            "test_int": pd.Series([1, 2, 3], dtype="Int64"),
            "test_float": pd.Series([1.1, 2.2, 3.3], dtype="float64"),
            "test_enum": pd.Series(['odd', 'even', 'odd'], dtype="object"),
            "test_null": pd.Series([None, None, None], dtype="Int64")
        }
    )
    assert_frame_equal(df, expected, check_names=True)


def test_mysql_with_partition(mysql_url: str) -> None:
    query = "select * from test_table"
    df = read_sql(
        mysql_url,
        query,
        partition_on="test_int",
        partition_range=(0, 10),
        partition_num=6,
    )
    expected = pd.DataFrame(
        index=range(6),
        data={
            "test_int": pd.Series([1, 2, 3, 4, 5, 6], dtype="Int64"),
            "test_float": pd.Series([1.1, 2.2, 3.3, 4.4, 5.5, 6.6], dtype="float64"),
            "test_enum": pd.Series(['odd', 'even', 'odd', 'even', 'odd', 'even'], dtype="object"),
            "test_null": pd.Series([None, None, None, None, None, None], dtype="Int64")
        }
    )
    assert_frame_equal(df, expected, check_names=True)


def test_read_sql_with_partition_without_partition_range(mysql_url: str) -> None:
    query = "SELECT * FROM test_table where test_float > 3"
    df = read_sql(
        mysql_url,
        query,
        partition_on="test_int",
        partition_num=3,
    )

    expected = pd.DataFrame(
        index=range(4),
        data={
            "test_int": pd.Series([3, 4, 5, 6], dtype="Int64"),
            "test_float": pd.Series([3.3, 4.4, 5.5, 6.6], dtype="float64"),
            "test_enum": pd.Series(['odd', 'even', 'odd', 'even'], dtype="object"),
            "test_null": pd.Series([None, None, None, None], dtype="Int64")
        }
    )
    assert_frame_equal(df, expected, check_names=True)


def test_mysql_manual_partition(mysql_url: str) -> None:
    queries = [
        "SELECT * FROM test_table WHERE test_int < 2",
        "SELECT * FROM test_table WHERE test_int >= 2",
    ]
    df = read_sql(
        mysql_url,
        query=queries)
    expected = pd.DataFrame(
        index=range(6),
        data={
            "test_int": pd.Series([1, 2, 3, 4, 5, 6], dtype="Int64"),
            "test_float": pd.Series([1.1, 2.2, 3.3, 4.4, 5.5, 6.6], dtype="float64"),
            "test_enum": pd.Series(['odd', 'even', 'odd', 'even', 'odd', 'even'], dtype="object"),
            "test_null": pd.Series([None, None, None, None, None, None], dtype="Int64"),
        }
    )
    assert_frame_equal(df, expected, check_names=True)


def test_mysql_selection_and_projection(mysql_url: str) -> None:
    query = "SELECT test_int FROM test_table WHERE test_float < 5"
    df = read_sql(
        mysql_url,
        query,
        partition_on="test_int",
        partition_num=3,
    )
    expected = pd.DataFrame(
        index=range(4),
        data={
            "test_int": pd.Series([1, 2, 3, 4], dtype="Int64"),
        }
    )
    assert_frame_equal(df, expected, check_names=True)


def test_mysql_join(mysql_url: str) -> None:
    query = "SELECT T.test_int, T.test_float, S.test_str FROM test_table T INNER JOIN test_table_extra S ON T.test_int = S.test_int"
    import pymysql
    env_dist = os.environ
    conn = pymysql.connect(user=env_dist.get('MYSQL_USER'), 
                           password=env_dist.get('MYSQL_PASSWORD'),
                           database=env_dist.get('MYSQL_DB'),
                           port=int(env_dist.get('MYSQL_PORT')),
                           host=env_dist.get('MYSQL_HOST'))
    df_pandas = pd.read_sql(query, conn)
    df = read_sql(
        mysql_url,
        query,
        partition_on="test_int",
        partition_num=3,
    )
    expected = pd.DataFrame(
        index=range(3),
        data={
            "test_int": pd.Series([1, 2, 3], dtype="Int64"),
            "test_float": pd.Series([1.1, 2.2, 3.3], dtype="float64"),
            "test_str": pd.Series(["Ha好ち😁ðy̆", "こんにちは", "русский",], dtype="object")
        }
    )
    print(df_pandas)
    print(df)
    print(expected)
    assert_frame_equal(df, expected, check_names=True)


def test_mysql_aggregate(mysql_url: str) -> None:
    query = "select AVG(test_float) as avg_float, SUM(T.test_int) as sum_int, SUM(test_null) as sum_null from test_table as T INNER JOIN test_table_extra as S where T.test_int = S.test_int GROUP BY test_enum ORDER BY sum_int"
    df = read_sql(mysql_url, query)
    expected = pd.DataFrame(
        index=range(2),
        data={
            "avg_float": pd.Series([2.2, 2.2], dtype="float64"),
            "sum_int": pd.Series([2.0, 4.0], dtype="float64"),
            "sum_null": pd.Series([None, None], dtype="float64"),
        },
    )
    assert_frame_equal(df, expected, check_names=True)


def test_mysql_types_binary(mysql_url: str) -> None:
    query = "select * from test_types"
    df = read_sql(mysql_url, query, protocol="binary")
    expected = pd.DataFrame(
        index=range(3),
        data={
            "test_timestamp": pd.Series(["1970-01-01 00:00:01", "2038-01-19 00:00:00", None], dtype="datetime64[ns]"),
            "test_date": pd.Series([None, "1970-01-01", "2038-01-19"], dtype="datetime64[ns]"),
            "test_time": pd.Series(["00:00:00", None, "23:59:59"], dtype="object"),
            "test_datetime": pd.Series(["1970-01-01 00:00:01", "2038-01-19 00:0:00", None], dtype="datetime64[ns]"),
            "test_new_decimal": pd.Series([1.1, None, 3.3], dtype="float"),
            "test_decimal": pd.Series([1, 2, None], dtype="float"),
            "test_varchar": pd.Series([None, "varchar2", "varchar3"], dtype="object"),
            "test_char": pd.Series(["char1", None, "char3"], dtype="object"),
            "test_tiny": pd.Series([-128, 127, None], dtype="Int64"),
            "test_short": pd.Series([-32768, 32767, None], dtype="Int64"),
            "test_int24": pd.Series([-8388608, 8388607, None], dtype="Int64"),
            "test_long": pd.Series([-2147483648, 2147483647, None], dtype="Int64"),
            "test_longlong": pd.Series([-9223372036854775808, 9223372036854775807, None], dtype="Int64"),
            "test_float": pd.Series([None, -1.1E-38, 3.4E38], dtype="float"),
            "test_double": pd.Series([-2.2E-308, None, 1.7E308], dtype="float"),
            "test_year": pd.Series([1901, 2155, None], dtype="Int64"),
            "test_tinyblob": pd.Series([None, b"tinyblob2", b"tinyblob3"], dtype="object"),
            "test_blob": pd.Series([None, b"blobblobblobblob2", b"blobblobblobblob3"], dtype="object"),
            "test_mediumblob": pd.Series([None, b"mediumblob2", b"mediumblob3"], dtype="object"),
            "test_longblob": pd.Series([None, b"longblob2", b"longblob3"], dtype="object"),
            "test_enum": pd.Series(["apple", None, "mango"], dtype="object"),
            "test_json": pd.Series(['{"age":1,"name":"piggy"}', '{"age":2,"name":"kitty"}', None], dtype="object")
        }
    )
    assert_frame_equal(df, expected, check_names=True)


def test_mysql_types_text(mysql_url: str) -> None:
    query = "select * from test_types"
    df = read_sql(mysql_url, query, protocol="text")
    expected = pd.DataFrame(
        index=range(3),
        data={
            "test_timestamp": pd.Series(["1970-01-01 00:00:01", "2038-01-19 00:00:00", None], dtype="datetime64[ns]"),
            "test_date": pd.Series([None, "1970-01-01", "2038-01-19"], dtype="datetime64[ns]"),
            "test_time": pd.Series(["00:00:00", None, "23:59:59"], dtype="object"),
            "test_datetime": pd.Series(["1970-01-01 00:00:01", "2038-01-19 00:00:00", None], dtype="datetime64[ns]"),
            "test_new_decimal": pd.Series([1.1, None, 3.3], dtype="float"),
            "test_decimal": pd.Series([1, 2, None], dtype="float"),
            "test_varchar": pd.Series([None, "varchar2", "varchar3"], dtype="object"),
            "test_char": pd.Series(["char1", None, "char3"], dtype="object"),
            "test_tiny": pd.Series([-128, 127, None], dtype="Int64"),
            "test_short": pd.Series([-32768, 32767, None], dtype="Int64"),
            "test_int24": pd.Series([-8388608, 8388607, None], dtype="Int64"),
            "test_long": pd.Series([-2147483648, 2147483647, None], dtype="Int64"),
            "test_longlong": pd.Series([-9223372036854775808, 9223372036854775807, None], dtype="Int64"),
            "test_float": pd.Series([None, -1.1E-38, 3.4E38], dtype="float"),
            "test_double": pd.Series([-2.2E-308, None, 1.7E308], dtype="float"),
            "test_year": pd.Series([1901, 2155, None], dtype="Int64"),
            "test_tinyblob": pd.Series([None, b"tinyblob2", b"tinyblob3"], dtype="object"),
            "test_blob": pd.Series([None, b"blobblobblobblob2", b"blobblobblobblob3"], dtype="object"),
            "test_mediumblob": pd.Series([None, b"mediumblob2", b"mediumblob3"], dtype="object"),
            "test_longblob": pd.Series([None, b"longblob2", b"longblob3"], dtype="object"),
            "test_enum": pd.Series(["apple", None, "mango"], dtype="object"),
            "test_json": pd.Series(['{"age":1,"name":"piggy"}', '{"age":2,"name":"kitty"}', None], dtype="object")
        }
    )
    assert_frame_equal(df, expected, check_names=True)


def test_empty_result(mysql_url: str) -> None:
    query = "SELECT * FROM test_table where test_int < -100"
    df = read_sql(mysql_url, query)
    expected = pd.DataFrame(
        data={
            "test_int": pd.Series([], dtype="object"),
            "test_float": pd.Series([], dtype="object"),
            "test_enum": pd.Series([], dtype="object"),
            "test_null": pd.Series([], dtype="object")
        }
    )
    assert_frame_equal(df, expected, check_names=True)


def test_empty_result_on_partition(mysql_url: str) -> None:
    query = "SELECT * FROM test_table where test_int < -100"
    df = read_sql(mysql_url, query, partition_on="test_int", partition_num=3)
    expected = pd.DataFrame(
        data={
            "test_int": pd.Series([], dtype="object"),
            "test_float": pd.Series([], dtype="object"),
            "test_enum": pd.Series([], dtype="object"),
            "test_null": pd.Series([], dtype="object")
        }
    )
    assert_frame_equal(df, expected, check_names=True)


def test_empty_result_on_some_partition(mysql_url: str) -> None:
    query = "SELECT * FROM test_table where test_int = 6"
    df = read_sql(mysql_url, query, partition_on="test_int", partition_num=3)
    expected = pd.DataFrame(
        index=range(1),
        data={
            "test_int": pd.Series([6], dtype="Int64"),
            "test_float": pd.Series([6.6], dtype="float64"),
            "test_enum": pd.Series(['even'], dtype="object"),
            "test_null": pd.Series([None], dtype="Int64")
        }
    )
    assert_frame_equal(df, expected, check_names=True)