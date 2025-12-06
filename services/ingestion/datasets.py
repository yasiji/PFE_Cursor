"""Dataset loading functions for FreshRetailNet-50K."""

from pathlib import Path
from typing import Optional

import pandas as pd
from datasets import load_dataset
from datasets.dataset_dict import DatasetDict

from shared.config import DataConfig, get_config
from shared.exceptions import DataLoadError
from shared.logging_setup import get_logger

logger = get_logger(__name__)


def load_freshretailnet_dataset(
    dataset_name: Optional[str] = None,
    cache_dir: Optional[str] = None,
    split: Optional[str] = None,
    use_local: bool = False,
) -> DatasetDict | pd.DataFrame:
    """
    Load the FreshRetailNet-50K dataset from HuggingFace or local files.

    Args:
        dataset_name: Name of the dataset (defaults to config value).
        cache_dir: Cache directory for downloaded dataset.
        split: Dataset split to load (e.g., "train", "test"). If None, loads all splits.
        use_local: If True, try to load from local files first.

    Returns:
        DatasetDict if split is None, or DataFrame if split is specified.

    Raises:
        DataLoadError: If dataset loading fails.
    """
    config = get_config()
    dataset_name = dataset_name or config.data.hf_dataset_name
    cache_dir = cache_dir or config.data.hf_cache_dir

    # Try local files first if requested
    if use_local:
        # Check for FreshRetailNet-50K in project root
        project_root = Path(__file__).parent.parent.parent
        freshretail_path = project_root / "FreshRetailNet-50K" / "data"
        
        if (freshretail_path / "train.parquet").exists():
            logger.info("Loading from local FreshRetailNet-50K dataset", path=str(freshretail_path))
            train_df = load_dataset_from_parquet(freshretail_path / "train.parquet")
            
            # Return as DatasetDict for consistency
            from datasets import Dataset
            dataset_dict = {"train": Dataset.from_pandas(train_df)}
            
            # Add eval split if exists
            if (freshretail_path / "eval.parquet").exists():
                eval_df = load_dataset_from_parquet(freshretail_path / "eval.parquet")
                dataset_dict["eval"] = Dataset.from_pandas(eval_df)
            
            if split:
                if split in dataset_dict:
                    return dataset_dict[split].to_pandas()
                else:
                    raise DataLoadError(f"Split '{split}' not found. Available: {list(dataset_dict.keys())}")
            return dataset_dict
        
        # Fallback to synthetic data if exists
        local_path = Path(config.data.dataset_path) / "synthetic_retail_data.parquet"
        if local_path.exists():
            logger.info("Loading from local synthetic file", path=str(local_path))
            df = load_dataset_from_parquet(local_path)
            from datasets import Dataset
            dataset_dict = {"train": Dataset.from_pandas(df)}
            if split:
                return df
            return dataset_dict

    try:
        logger.info(
            "Loading dataset",
            dataset_name=dataset_name,
            cache_dir=cache_dir,
            split=split,
        )

        # Load dataset from HuggingFace
        dataset = load_dataset(dataset_name, cache_dir=cache_dir)

        if split:
            # Return specific split as DataFrame
            if split not in dataset:
                raise DataLoadError(f"Split '{split}' not found in dataset. Available splits: {list(dataset.keys())}")
            return dataset[split].to_pandas()

        # Return all splits as DatasetDict
        return dataset

    except Exception as e:
        logger.warning("Failed to load from HuggingFace, trying local files", error=str(e))
        # Fallback to local files
        local_path = Path(config.data.dataset_path) / "synthetic_retail_data.parquet"
        if local_path.exists():
            logger.info("Loading from local file as fallback", path=str(local_path))
            df = load_dataset_from_parquet(local_path)
            from datasets import Dataset
            dataset_dict = {"train": Dataset.from_pandas(df)}
            if split:
                return df
            return dataset_dict
        else:
            logger.error("Failed to load dataset", error=str(e), exc_info=True)
            raise DataLoadError(f"Failed to load dataset '{dataset_name}': {str(e)}") from e


def save_dataset_to_parquet(
    dataset: pd.DataFrame,
    output_path: Path | str,
    partition_by: Optional[list[str]] = None,
) -> None:
    """
    Save dataset to parquet format.

    Args:
        dataset: DataFrame to save.
        output_path: Output file or directory path.
        partition_by: Optional list of columns to partition by.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if partition_by:
        dataset.to_parquet(
            output_path,
            partition_cols=partition_by,
            engine="pyarrow",
        )
        logger.info(
            "Saved partitioned dataset",
            output_path=str(output_path),
            partition_by=partition_by,
        )
    else:
        dataset.to_parquet(output_path, engine="pyarrow")
        logger.info("Saved dataset", output_path=str(output_path))


def load_dataset_from_parquet(
    input_path: Path | str,
    columns: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Load dataset from parquet format.

    Args:
        input_path: Input file or directory path.
        columns: Optional list of columns to load.

    Returns:
        Loaded DataFrame.
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise DataLoadError(f"Dataset file not found: {input_path}")

    try:
        df = pd.read_parquet(input_path, columns=columns, engine="pyarrow")
        logger.info("Loaded dataset", input_path=str(input_path), rows=len(df))
        return df
    except Exception as e:
        logger.error("Failed to load dataset from parquet", error=str(e), exc_info=True)
        raise DataLoadError(f"Failed to load dataset from '{input_path}': {str(e)}") from e

