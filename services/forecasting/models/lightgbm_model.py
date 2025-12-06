"""LightGBM forecasting model implementation."""

from typing import Dict, List, Optional

import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib

from services.forecasting.models.base import BaseForecastModel
from shared.logging_setup import get_logger

logger = get_logger(__name__)


class LightGBMForecaster(BaseForecastModel):
    """LightGBM-based forecasting model."""

    def __init__(
        self,
        name: str = "lightgbm",
        params: Optional[Dict] = None,
        num_boost_round: int = 100,
        early_stopping_rounds: int = 10
    ):
        """
        Initialize LightGBM forecaster.

        Args:
            name: Model name
            params: LightGBM parameters (if None, use defaults)
            num_boost_round: Number of boosting rounds
            early_stopping_rounds: Early stopping rounds
        """
        super().__init__(name=name)
        self.model: Optional[lgb.Booster] = None
        self.params = params or self._get_default_params()
        self.num_boost_round = num_boost_round
        self.early_stopping_rounds = early_stopping_rounds
        self.feature_cols: Optional[List[str]] = None
        self.feature_importance: Optional[Dict[str, float]] = None

    @staticmethod
    def _get_default_params() -> Dict:
        """Get default LightGBM parameters."""
        return {
            'objective': 'regression',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'force_col_wise': True
        }

    def train(
        self,
        train_data: pd.DataFrame,
        target_col: str,
        feature_cols: Optional[List[str]] = None,
        val_data: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> None:
        """
        Train the LightGBM model.

        Args:
            train_data: Training data DataFrame
            target_col: Name of the target column
            feature_cols: List of feature column names (if None, use all except target)
            val_data: Validation data DataFrame (optional)
            **kwargs: Additional training parameters
        """
        if target_col not in train_data.columns:
            raise ValueError(f"Target column '{target_col}' not found in training data")

        # Determine feature columns
        if feature_cols is None:
            feature_cols = [col for col in train_data.columns 
                          if col != target_col and train_data[col].dtype in ['int64', 'float64']]
        
        self.feature_cols = feature_cols

        # Prepare training data
        X_train = train_data[feature_cols].copy()
        y_train = train_data[target_col].copy()

        # Handle missing values
        X_train = X_train.fillna(0)

        # Create LightGBM dataset
        train_dataset = lgb.Dataset(X_train, label=y_train)

        # Prepare validation data if provided
        valid_sets = [train_dataset]
        valid_names = ['train']
        
        if val_data is not None:
            X_val = val_data[feature_cols].copy().fillna(0)
            y_val = val_data[target_col].copy()
            val_dataset = lgb.Dataset(X_val, label=y_val, reference=train_dataset)
            valid_sets.append(val_dataset)
            valid_names.append('valid')

        # Train model
        logger.info(f"Training LightGBM model with {len(feature_cols)} features")
        
        self.model = lgb.train(
            self.params,
            train_dataset,
            num_boost_round=self.num_boost_round,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=[
                lgb.early_stopping(stopping_rounds=self.early_stopping_rounds),
                lgb.log_evaluation(period=10)
            ] if val_data is not None else [lgb.log_evaluation(period=10)]
        )

        # Store feature importance
        importance = self.model.feature_importance(importance_type='gain')
        self.feature_importance = dict(zip(feature_cols, importance))

        self.is_trained = True
        logger.info("LightGBM model trained successfully")

    def predict(
        self,
        data: pd.DataFrame,
        horizon: int = 1,
        feature_cols: Optional[List[str]] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        Generate forecasts using LightGBM.

        Args:
            data: Input data DataFrame
            horizon: Forecast horizon (number of periods ahead)
            feature_cols: List of feature column names (if None, use trained features)
            **kwargs: Additional prediction parameters

        Returns:
            DataFrame with forecasts
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before prediction")
        
        if self.model is None:
            raise ValueError("Model not initialized")

        # Use trained feature columns if not specified
        if feature_cols is None:
            feature_cols = self.feature_cols

        if feature_cols is None:
            raise ValueError("Feature columns must be specified")

        # Prepare features
        X = data[feature_cols].copy().fillna(0)

        # Generate predictions
        predictions = self.model.predict(X, num_iteration=self.model.best_iteration)

        # Create result DataFrame
        result = pd.DataFrame({
            'predicted_demand': predictions,
            'lower_bound': predictions * 0.8,  # Simple bounds (can be improved)
            'upper_bound': predictions * 1.2
        })

        return result

    def save(self, path: str) -> None:
        """
        Save model to disk.

        Args:
            path: Path to save the model
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")

        model_data = {
            'model': self.model,
            'params': self.params,
            'feature_cols': self.feature_cols,
            'feature_importance': self.feature_importance,
            'name': self.name
        }

        joblib.dump(model_data, path)
        logger.info(f"Model saved to {path}")

    def load(self, path: str) -> None:
        """
        Load model from disk.

        Args:
            path: Path to load the model from
        """
        model_data = joblib.load(path)
        
        self.model = model_data['model']
        self.params = model_data['params']
        self.feature_cols = model_data['feature_cols']
        self.feature_importance = model_data.get('feature_importance')
        self.name = model_data.get('name', 'lightgbm')
        self.is_trained = True

        logger.info(f"Model loaded from {path}")

    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance scores."""
        return self.feature_importance

