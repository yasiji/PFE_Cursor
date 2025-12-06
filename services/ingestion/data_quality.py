"""Data quality validation and checks."""

from typing import Dict, List, Optional

import pandas as pd
import numpy as np

from shared.logging_setup import get_logger

logger = get_logger(__name__)


class DataQualityReport:
    """Data quality report for a dataset."""

    def __init__(self, df: pd.DataFrame, name: str = "dataset"):
        """
        Initialize data quality report.

        Args:
            df: DataFrame to analyze
            name: Name of the dataset for reporting
        """
        self.df = df
        self.name = name
        self.issues: List[Dict] = []

    def check_completeness(self) -> pd.DataFrame:
        """
        Check for missing values.

        Returns:
            DataFrame with missing value counts and percentages.
        """
        missing = self.df.isnull().sum()
        missing_pct = (missing / len(self.df) * 100).round(2)
        
        result = pd.DataFrame({
            'Missing Count': missing,
            'Missing %': missing_pct
        })
        
        # Log issues
        high_missing = result[result['Missing %'] > 10]
        if len(high_missing) > 0:
            for col in high_missing.index:
                self.issues.append({
                    'type': 'high_missing_values',
                    'column': col,
                    'missing_pct': high_missing.loc[col, 'Missing %'],
                    'severity': 'warning' if high_missing.loc[col, 'Missing %'] < 50 else 'error'
                })
        
        return result

    def check_consistency(self) -> List[Dict]:
        """
        Check data consistency (negative values, invalid ranges, etc.).

        Returns:
            List of consistency issues found.
        """
        issues = []
        
        # Check numeric columns for negative values where they shouldn't be
        numeric_cols = self.df.select_dtypes(include=['number']).columns
        for col in numeric_cols:
            if 'quantity' in col.lower() or 'sales' in col.lower() or 'stock' in col.lower():
                negative_count = (self.df[col] < 0).sum()
                if negative_count > 0:
                    issues.append({
                        'type': 'negative_values',
                        'column': col,
                        'count': negative_count,
                        'severity': 'error'
                    })
        
        # Check for duplicates (exclude array columns)
        try:
            # Identify array columns
            array_cols = []
            for col in self.df.columns:
                if self.df[col].dtype == 'object':
                    sample = self.df[col].dropna()
                    if len(sample) > 0:
                        first_val = sample.iloc[0]
                        if isinstance(first_val, (list, np.ndarray)):
                            array_cols.append(col)
            
            # Check duplicates excluding array columns
            if array_cols:
                cols_to_check = [c for c in self.df.columns if c not in array_cols]
                duplicates = self.df[cols_to_check].duplicated().sum()
            else:
                duplicates = self.df.duplicated().sum()
            
            if duplicates > 0:
                issues.append({
                    'type': 'duplicate_rows',
                    'count': duplicates,
                    'percentage': (duplicates / len(self.df) * 100).round(2),
                    'severity': 'warning'
                })
        except Exception as e:
            # Skip duplicate check if it fails (e.g., due to array columns)
            pass
        
        self.issues.extend(issues)
        return issues

    def check_outliers(self, method: str = 'iqr', threshold: float = 3.0) -> Dict[str, pd.DataFrame]:
        """
        Detect outliers in numeric columns.

        Args:
            method: Method to use ('iqr' or 'zscore')
            threshold: Threshold for outlier detection

        Returns:
            Dictionary mapping column names to outlier DataFrames.
        """
        outliers = {}
        numeric_cols = self.df.select_dtypes(include=['number']).columns
        
        for col in numeric_cols:
            if method == 'iqr':
                Q1 = self.df[col].quantile(0.25)
                Q3 = self.df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                outlier_mask = (self.df[col] < lower_bound) | (self.df[col] > upper_bound)
            else:  # zscore
                z_scores = (self.df[col] - self.df[col].mean()) / self.df[col].std()
                outlier_mask = abs(z_scores) > threshold
            
            outlier_count = outlier_mask.sum()
            if outlier_count > 0:
                outliers[col] = self.df[outlier_mask][[col]]
                outlier_pct = (outlier_count / len(self.df) * 100).round(2)
                
                if outlier_pct > 5:  # More than 5% outliers
                    self.issues.append({
                        'type': 'high_outlier_rate',
                        'column': col,
                        'outlier_count': outlier_count,
                        'outlier_pct': outlier_pct,
                        'severity': 'warning'
                    })
        
        return outliers

    def check_timestamps(self, timestamp_cols: Optional[List[str]] = None) -> List[Dict]:
        """
        Check timestamp columns for validity and ordering.

        Args:
            timestamp_cols: List of timestamp column names. If None, auto-detect.

        Returns:
            List of timestamp-related issues.
        """
        issues = []
        
        if timestamp_cols is None:
            # Auto-detect timestamp columns
            timestamp_cols = self.df.select_dtypes(include=['datetime64']).columns.tolist()
            # Also check object columns that might be timestamps
            for col in self.df.select_dtypes(include=['object']).columns:
                if any(keyword in col.lower() for keyword in ['date', 'time', 'timestamp']):
                    timestamp_cols.append(col)
        
        for col in timestamp_cols:
            if col not in self.df.columns:
                continue
            
            # Try to convert to datetime if not already
            try:
                if self.df[col].dtype == 'object':
                    ts_series = pd.to_datetime(self.df[col], errors='coerce')
                else:
                    ts_series = self.df[col]
                
                # Check for invalid dates
                invalid_count = ts_series.isnull().sum() - self.df[col].isnull().sum()
                if invalid_count > 0:
                    issues.append({
                        'type': 'invalid_timestamps',
                        'column': col,
                        'count': invalid_count,
                        'severity': 'error'
                    })
                
                # Check date range
                if ts_series.notna().any():
                    min_date = ts_series.min()
                    max_date = ts_series.max()
                    if (max_date - min_date).days < 0:
                        issues.append({
                            'type': 'invalid_date_range',
                            'column': col,
                            'min': min_date,
                            'max': max_date,
                            'severity': 'error'
                        })
            except Exception as e:
                logger.warning(f"Could not check timestamp column {col}: {e}")
        
        self.issues.extend(issues)
        return issues

    def generate_report(self) -> Dict:
        """
        Generate a comprehensive data quality report.

        Returns:
            Dictionary with report summary.
        """
        report = {
            'name': self.name,
            'shape': self.df.shape,
            'columns': list(self.df.columns),
            'dtypes': self.df.dtypes.to_dict(),
            'missing_values': self.check_completeness().to_dict('index'),
            'consistency_issues': self.check_consistency(),
            'timestamp_issues': self.check_timestamps(),
            'all_issues': self.issues,
            'summary': {
                'total_rows': len(self.df),
                'total_columns': len(self.df.columns),
                'total_issues': len(self.issues),
                'error_count': sum(1 for issue in self.issues if issue.get('severity') == 'error'),
                'warning_count': sum(1 for issue in self.issues if issue.get('severity') == 'warning'),
            }
        }
        
        return report


def validate_data_quality(df: pd.DataFrame, name: str = "dataset") -> DataQualityReport:
    """
    Validate data quality and generate a report.

    Args:
        df: DataFrame to validate
        name: Name of the dataset

    Returns:
        DataQualityReport instance
    """
    report = DataQualityReport(df, name)
    report.generate_report()
    return report

