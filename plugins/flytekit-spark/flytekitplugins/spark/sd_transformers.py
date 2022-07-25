import typing

from pyspark.sql.dataframe import DataFrame

from flytekit import FlyteContext
from flytekit.models import literals
from flytekit.models.literals import StructuredDatasetMetadata
from flytekit.models.types import StructuredDatasetType
from flytekit.types.structured.structured_dataset import (
    ABFS,
    GCS,
    LOCAL,
    PARQUET,
    S3,
    StructuredDataset,
    StructuredDatasetDecoder,
    StructuredDatasetEncoder,
    StructuredDatasetTransformerEngine,
)


class SparkToParquetEncodingHandler(StructuredDatasetEncoder):
    def __init__(self, protocol: str):
        super().__init__(DataFrame, protocol, PARQUET)

    def encode(
        self,
        ctx: FlyteContext,
        structured_dataset: StructuredDataset,
        structured_dataset_type: StructuredDatasetType,
    ) -> literals.StructuredDataset:
        path = typing.cast(str, structured_dataset.uri) or ctx.file_access.get_random_remote_directory()
        df = typing.cast(DataFrame, structured_dataset.dataframe)
        df.write.mode("overwrite").parquet(path)
        return literals.StructuredDataset(uri=path, metadata=StructuredDatasetMetadata(structured_dataset_type))


class ParquetToSparkDecodingHandler(StructuredDatasetDecoder):
    def __init__(self, protocol: str):
        super().__init__(DataFrame, protocol, PARQUET)

    def decode(
        self,
        ctx: FlyteContext,
        flyte_value: literals.StructuredDataset,
        current_task_metadata: StructuredDatasetMetadata,
    ) -> DataFrame:
        user_ctx = FlyteContext.current_context().user_space_params
        if current_task_metadata.structured_dataset_type and current_task_metadata.structured_dataset_type.columns:
            columns = [c.name for c in current_task_metadata.structured_dataset_type.columns]
            return user_ctx.spark_session.read.parquet(flyte_value.uri).select(*columns)
        return user_ctx.spark_session.read.parquet(flyte_value.uri)


for protocol in [LOCAL, S3, GCS, ABFS]:
    StructuredDatasetTransformerEngine.register(SparkToParquetEncodingHandler(protocol), default_for_type=False)
    StructuredDatasetTransformerEngine.register(ParquetToSparkDecodingHandler(protocol), default_for_type=False)
