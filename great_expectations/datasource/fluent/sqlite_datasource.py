from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    Union,
    cast,
)

from great_expectations._docs_decorators import public_api
from great_expectations.compatibility import pydantic
from great_expectations.compatibility.sqlalchemy import sqlalchemy as sa
from great_expectations.compatibility.typing_extensions import override
from great_expectations.core.partitioners import (
    PartitionerConvertedDatetime,
)
from great_expectations.datasource.fluent.config_str import (
    ConfigStr,
    _check_config_substitutions_needed,
)
from great_expectations.datasource.fluent.sql_datasource import (
    QueryAsset as SqlQueryAsset,
)
from great_expectations.datasource.fluent.sql_datasource import (
    SQLDatasource,
    SqlitePartitionerConvertedDateTime,
    _PartitionerOneColumnOneParam,
)
from great_expectations.datasource.fluent.sql_datasource import (
    TableAsset as SqlTableAsset,
)

if TYPE_CHECKING:
    # min version of typing_extension missing `Self`, so it can't be imported at runtime

    from great_expectations.datasource.fluent.interfaces import (
        BatchMetadata,
        BatchRequestOptions,
        DataAsset,
        SortersDefinition,
    )

# This module serves as an example of how to extend _SQLAssets for specific backends. The steps are:
# 1. Create a plain class with the extensions necessary for the specific backend.
# 2. Make 2 classes XTableAsset and XQueryAsset by mixing in the class created in step 1 with
#    sql_datasource.TableAsset and sql_datasource.QueryAsset.
#
# See SqliteDatasource, SqliteTableAsset, and SqliteQueryAsset below.


class PartitionerConvertedDateTime(_PartitionerOneColumnOneParam):
    """A partitioner than can be used for sql engines that represents datetimes as strings.

    The SQL engine that this currently supports is SQLite since it stores its datetimes as
    strings.
    The DatetimePartitioner will also work for SQLite and may be more intuitive.
    """

    # date_format_strings syntax is documented here:
    # https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes
    # It allows for arbitrary strings so can't be validated until conversion time.
    date_format_string: str
    column_name: str
    method_name: Literal["partition_on_converted_datetime"] = "partition_on_converted_datetime"

    @property
    @override
    def param_names(self) -> List[str]:
        # The datetime parameter will be a string representing a datetime in the format
        # given by self.date_format_string.
        return ["datetime"]

    @override
    def partitioner_method_kwargs(self) -> Dict[str, Any]:
        return {
            "column_name": self.column_name,
            "date_format_string": self.date_format_string,
        }

    @override
    def batch_request_options_to_batch_spec_kwarg_identifiers(
        self, options: BatchRequestOptions
    ) -> Dict[str, Any]:
        if "datetime" not in options:
            raise ValueError(
                "'datetime' must be specified in the batch request options to create a batch identifier"  # noqa: E501
            )
        return {self.column_name: options["datetime"]}


class SqliteDsn(pydantic.AnyUrl):
    allowed_schemes = {
        "sqlite",
        "sqlite+pysqlite",
        "sqlite+aiosqlite",
        "sqlite+pysqlcipher",
    }
    host_required = False


class SqliteTableAsset(SqlTableAsset):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # update the partitioner map with the Sqlite specific partitioner
        self._partitioner_implementation_map[PartitionerConvertedDatetime] = (
            SqlitePartitionerConvertedDateTime
        )

    type: Literal["table"] = "table"


class SqliteQueryAsset(SqlQueryAsset):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # update the partitioner map with the  Sqlite specific partitioner
        self._partitioner_implementation_map[PartitionerConvertedDatetime] = (
            SqlitePartitionerConvertedDateTime
        )

    type: Literal["query"] = "query"


@public_api
class SqliteDatasource(SQLDatasource):
    """Adds a sqlite datasource to the data context.

    Args:
        name: The name of this sqlite datasource.
        connection_string: The SQLAlchemy connection string used to connect to the sqlite database.
            For example: "sqlite:///path/to/file.db"
        create_temp_table: Whether to leverage temporary tables during metric computation.
        assets: An optional dictionary whose keys are TableAsset names and whose values
            are TableAsset objects.
    """

    # class var definitions
    asset_types: ClassVar[List[Type[DataAsset]]] = [SqliteTableAsset, SqliteQueryAsset]

    if sa:  # sqlalchemy might not be installed
        _poolclass: ClassVar[Optional[Type[sa.pool.Pool]]] = sa.pool.StaticPool
    else:
        _poolclass = None

    # Subclass instance var overrides
    # right side of the operator determines the type name
    # left side enforces the names on instance creation
    type: Literal["sqlite"] = "sqlite"  # type: ignore[assignment]
    connection_string: Union[ConfigStr, SqliteDsn]

    _TableAsset: Type[SqlTableAsset] = pydantic.PrivateAttr(SqliteTableAsset)
    _QueryAsset: Type[SqlQueryAsset] = pydantic.PrivateAttr(SqliteQueryAsset)

    @override
    def _create_engine(self) -> sa.engine.Engine:
        """
        Create the engine from the connection string, applying config substitutions.
        Also set the poolclass to StaticPool to avoid issues with multithreading.
        """
        model_dict = self.dict(
            exclude=self._get_exec_engine_excludes(),
            config_provider=self._config_provider,
        )
        _check_config_substitutions_needed(
            self, model_dict, raise_warning_if_provider_not_present=True
        )
        # the connection_string has had config substitutions applied
        connection_string = model_dict.pop("connection_string")
        kwargs = model_dict.pop("kwargs", {})
        # if needed a user could set a different `_poolclass` on the datasource.
        return sa.create_engine(connection_string, poolclass=self._poolclass, **kwargs)

    @public_api
    @override
    def add_table_asset(  # noqa: PLR0913
        self,
        name: str,
        table_name: str = "",
        schema_name: Optional[str] = None,
        order_by: Optional[SortersDefinition] = None,
        batch_metadata: Optional[BatchMetadata] = None,
    ) -> SqliteTableAsset:
        return cast(
            SqliteTableAsset,
            super().add_table_asset(
                name=name,
                table_name=table_name,
                schema_name=schema_name,
                order_by=order_by,
                batch_metadata=batch_metadata,
            ),
        )

    add_table_asset.__doc__ = SQLDatasource.add_table_asset.__doc__

    @public_api
    @override
    def add_query_asset(
        self,
        name: str,
        query: str,
        order_by: Optional[SortersDefinition] = None,
        batch_metadata: Optional[BatchMetadata] = None,
    ) -> SqliteQueryAsset:
        return cast(
            SqliteQueryAsset,
            super().add_query_asset(
                name=name, query=query, order_by=order_by, batch_metadata=batch_metadata
            ),
        )

    add_query_asset.__doc__ = SQLDatasource.add_query_asset.__doc__
