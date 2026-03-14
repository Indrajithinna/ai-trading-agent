"""
AI Prediction Model (Module 7)
================================
Machine learning classifier using RandomForest and XGBoost.
Features: RSI, MACD, EMA9, EMA21, VWAP, ATR, Volume
Trade only when probability > 70%.
"""

import os
import pickle
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

import pandas as pd
import numpy as np

from ai_trading_agent.config import AIModelConfig
from ai_trading_agent.utils.logger import get_logger

logger = get_logger("AIPredictionModel")


class AIPredictionModel:
    """
    ML-based trade prediction model.
    
    Uses ensemble of RandomForest and XGBoost classifiers
    to predict: BUY_CALL, BUY_PUT, or HOLD.
    
    Features used:
    - RSI, MACD, MACD_Signal, MACD_Hist
    - EMA9, EMA21
    - VWAP, ATR
    - Volume, Volume_Ratio
    - ADX, Trend_Strength
    - BB_Upper, BB_Lower
    """
    
    def __init__(self, config: AIModelConfig):
        self.config = config
        self.rf_model = None
        self.xgb_model = None
        self._is_trained = False
        self._feature_names = config.features
        self._label_map = {0: "HOLD", 1: "BUY_CALL", 2: "BUY_PUT"}
        self._training_metrics: Dict[str, float] = {}
        
        # Create save directory
        os.makedirs(config.model_save_path, exist_ok=True)
        
        logger.info("AIPredictionModel initialized")
    
    def train(self, df: pd.DataFrame, target_col: str = "target") -> Dict[str, float]:
        """
        Train the ensemble model.
        
        Args:
            df: DataFrame with features and target column
            target_col: Name of the target column (0=HOLD, 1=BUY_CALL, 2=BUY_PUT)
            
        Returns:
            Dictionary of training metrics
        """
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, classification_report
            
            # Prepare features
            available_features = [f for f in self._feature_names if f in df.columns]
            if len(available_features) < 3:
                logger.warning("Too few features available for training")
                return {"status": "failed", "reason": "insufficient_features"}
            
            X = df[available_features].copy()
            
            # Generate target if not present
            if target_col not in df.columns:
                df = self._generate_target_labels(df)
                if target_col not in df.columns:
                    return {"status": "failed", "reason": "no_target"}
            
            y = df[target_col]
            
            # Handle NaN
            mask = ~(X.isna().any(axis=1) | y.isna())
            X = X[mask]
            y = y[mask]
            
            if len(X) < 50:
                logger.warning(f"Only {len(X)} samples available. Training on synthetic data.")
                X, y = self._generate_synthetic_data(available_features, 500)
            
            # Split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config.test_size, random_state=42, stratify=y
            )
            
            # Train RandomForest
            self.rf_model = RandomForestClassifier(
                n_estimators=self.config.rf_n_estimators,
                max_depth=self.config.rf_max_depth,
                min_samples_split=self.config.rf_min_samples_split,
                random_state=42,
                n_jobs=-1
            )
            self.rf_model.fit(X_train, y_train)
            rf_acc = accuracy_score(y_test, self.rf_model.predict(X_test))
            
            # Train XGBoost
            try:
                from xgboost import XGBClassifier
                self.xgb_model = XGBClassifier(
                    n_estimators=self.config.xgb_n_estimators,
                    max_depth=self.config.xgb_max_depth,
                    learning_rate=self.config.xgb_learning_rate,
                    random_state=42,
                    use_label_encoder=False,
                    eval_metric='mlogloss'
                )
                self.xgb_model.fit(X_train, y_train)
                xgb_acc = accuracy_score(y_test, self.xgb_model.predict(X_test))
            except ImportError:
                logger.warning("XGBoost not installed. Using RandomForest only.")
                self.xgb_model = None
                xgb_acc = 0.0
            
            self._is_trained = True
            self._feature_names_trained = available_features
            
            self._training_metrics = {
                "rf_accuracy": round(rf_acc, 4),
                "xgb_accuracy": round(xgb_acc, 4),
                "ensemble_accuracy": round((rf_acc + xgb_acc) / 2 if xgb_acc > 0 else rf_acc, 4),
                "train_samples": len(X_train),
                "test_samples": len(X_test),
                "features_used": len(available_features),
                "trained_at": datetime.now().isoformat()
            }
            
            logger.info(
                f"✅ Model trained | RF: {rf_acc:.2%} | XGB: {xgb_acc:.2%} | "
                f"Samples: {len(X)}"
            )
            
            # Save models
            self._save_models()
            
            return self._training_metrics
            
        except ImportError as e:
            logger.error(f"Required library not installed: {e}")
            return {"status": "failed", "reason": str(e)}
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {"status": "failed", "reason": str(e)}
    
    def predict(self, features: pd.DataFrame) -> Dict[str, Any]:
        """
        Predict trade direction with probability.
        
        Args:
            features: DataFrame with feature columns
            
        Returns:
            Dictionary with prediction, probability, and details
        """
        if not self._is_trained:
            # Try to load saved model
            if not self._load_models():
                # Generate synthetic training
                logger.info("No trained model found. Training on synthetic data...")
                self._train_on_synthetic()
        
        if not self._is_trained:
            return {
                "prediction": "HOLD",
                "probability": 0.5,
                "confidence": 0,
                "model_status": "untrained"
            }
        
        try:
            # Align features
            feature_names = getattr(self, '_feature_names_trained', self._feature_names)
            available = [f for f in feature_names if f in features.columns]
            
            if len(available) < 3:
                return {
                    "prediction": "HOLD",
                    "probability": 0.5,
                    "confidence": 0,
                    "model_status": "insufficient_features"
                }
            
            X = features[available].iloc[[-1]].copy()
            X = X.fillna(0)
            
            # Ensemble prediction
            probabilities = []
            predictions = []
            
            if self.rf_model:
                rf_proba = self.rf_model.predict_proba(X)[0]
                rf_pred = self.rf_model.predict(X)[0]
                probabilities.append(rf_proba)
                predictions.append(rf_pred)
            
            if self.xgb_model:
                xgb_proba = self.xgb_model.predict_proba(X)[0]
                xgb_pred = self.xgb_model.predict(X)[0]
                probabilities.append(xgb_proba)
                predictions.append(xgb_pred)
            
            if not probabilities:
                return {
                    "prediction": "HOLD",
                    "probability": 0.5,
                    "confidence": 0,
                    "model_status": "no_model"
                }
            
            # Average probabilities
            avg_proba = np.mean(probabilities, axis=0)
            pred_class = int(np.argmax(avg_proba))
            max_proba = float(avg_proba[pred_class])
            
            prediction = self._label_map.get(pred_class, "HOLD")
            
            result = {
                "prediction": prediction,
                "probability": round(max_proba, 4),
                "confidence": round(max_proba * 100, 2),
                "class_probabilities": {
                    self._label_map[i]: round(float(p), 4) 
                    for i, p in enumerate(avg_proba)
                },
                "model_status": "active",
                "features_used": len(available)
            }
            
            logger.debug(
                f"AI Prediction: {prediction} | "
                f"Probability: {max_proba:.2%} | "
                f"Classes: {result['class_probabilities']}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {
                "prediction": "HOLD",
                "probability": 0.5,
                "confidence": 0,
                "model_status": f"error: {str(e)}"
            }
    
    def _generate_target_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate target labels from price action."""
        df = df.copy()
        
        # Target: future 5-bar return
        future_return = df['close'].shift(-5) / df['close'] - 1
        
        # Labels: 0=HOLD, 1=BUY_CALL, 2=BUY_PUT
        threshold = 0.002  # 0.2%
        df['target'] = 0  # HOLD
        df.loc[future_return > threshold, 'target'] = 1   # BUY_CALL
        df.loc[future_return < -threshold, 'target'] = 2  # BUY_PUT
        
        # Drop rows with NaN targets
        df = df.dropna(subset=['target'])
        df['target'] = df['target'].astype(int)
        
        return df
    
    def _generate_synthetic_data(self, feature_names: List[str], 
                                n_samples: int) -> Tuple[pd.DataFrame, pd.Series]:
        """Generate synthetic training data for initial model."""
        np.random.seed(42)
        
        data = {}
        for feat in feature_names:
            if feat == 'RSI':
                data[feat] = np.random.uniform(20, 80, n_samples)
            elif feat in ('MACD', 'MACD_Signal', 'MACD_Hist'):
                data[feat] = np.random.normal(0, 2, n_samples)
            elif feat in ('EMA9', 'EMA21'):
                data[feat] = np.random.uniform(23000, 25000, n_samples)
            elif feat == 'VWAP':
                data[feat] = np.random.uniform(23000, 25000, n_samples)
            elif feat == 'ATR':
                data[feat] = np.random.uniform(50, 200, n_samples)
            elif feat in ('Volume', 'Volume_Ratio'):
                data[feat] = np.random.uniform(0.5, 3.0, n_samples)
            elif feat in ('ADX', 'Trend_Strength'):
                data[feat] = np.random.uniform(10, 50, n_samples)
            else:
                data[feat] = np.random.normal(0, 1, n_samples)
        
        X = pd.DataFrame(data)
        
        # Generate correlated targets
        rsi = X.get('RSI', pd.Series(np.random.uniform(30, 70, n_samples)))
        macd = X.get('MACD_Hist', pd.Series(np.random.normal(0, 1, n_samples)))
        
        y = pd.Series(np.zeros(n_samples, dtype=int))
        y[(rsi > 60) & (macd > 0)] = 1  # BUY_CALL
        y[(rsi < 40) & (macd < 0)] = 2  # BUY_PUT
        
        # Add some noise
        noise_idx = np.random.choice(n_samples, size=int(n_samples * 0.1), replace=False)
        y.iloc[noise_idx] = np.random.randint(0, 3, size=len(noise_idx))
        
        return X, y
    
    def _train_on_synthetic(self):
        """Train model on synthetic data for paper trading."""
        features = [f for f in self._feature_names if f in [
            'RSI', 'MACD', 'MACD_Signal', 'MACD_Hist',
            'EMA9', 'EMA21', 'VWAP', 'ATR', 'Volume_Ratio',
            'ADX', 'Trend_Strength', 'BB_Upper', 'BB_Lower'
        ]]
        
        if not features:
            features = self._feature_names[:7]
        
        X, y = self._generate_synthetic_data(features, 1000)
        
        df = X.copy()
        df['target'] = y
        
        self.train(df)
    
    def _save_models(self):
        """Save trained models to disk."""
        try:
            if self.rf_model:
                path = os.path.join(self.config.model_save_path, "rf_model.pkl")
                with open(path, 'wb') as f:
                    pickle.dump(self.rf_model, f)
            
            if self.xgb_model:
                path = os.path.join(self.config.model_save_path, "xgb_model.pkl")
                with open(path, 'wb') as f:
                    pickle.dump(self.xgb_model, f)
            
            # Save feature names
            path = os.path.join(self.config.model_save_path, "feature_names.pkl")
            with open(path, 'wb') as f:
                pickle.dump(getattr(self, '_feature_names_trained', self._feature_names), f)
            
            logger.info("💾 Models saved to disk")
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    def _load_models(self) -> bool:
        """Load trained models from disk."""
        try:
            rf_path = os.path.join(self.config.model_save_path, "rf_model.pkl")
            if os.path.exists(rf_path):
                with open(rf_path, 'rb') as f:
                    self.rf_model = pickle.load(f)
                
                # Load feature names
                fn_path = os.path.join(self.config.model_save_path, "feature_names.pkl")
                if os.path.exists(fn_path):
                    with open(fn_path, 'rb') as f:
                        self._feature_names_trained = pickle.load(f)
                
                # Load XGBoost if available
                xgb_path = os.path.join(self.config.model_save_path, "xgb_model.pkl")
                if os.path.exists(xgb_path):
                    with open(xgb_path, 'rb') as f:
                        self.xgb_model = pickle.load(f)
                
                self._is_trained = True
                logger.info("📂 Models loaded from disk")
                return True
                
        except Exception as e:
            logger.error(f"Error loading models: {e}")
        
        return False
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the trained model."""
        if not self._is_trained or not self.rf_model:
            return {}
        
        feature_names = getattr(self, '_feature_names_trained', self._feature_names)
        importances = self.rf_model.feature_importances_
        
        return dict(sorted(
            zip(feature_names, importances),
            key=lambda x: x[1], reverse=True
        ))
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model status and metrics."""
        return {
            "is_trained": self._is_trained,
            "training_metrics": self._training_metrics,
            "feature_importance": self.get_feature_importance(),
            "features": self._feature_names,
        }
