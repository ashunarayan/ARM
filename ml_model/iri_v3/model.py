"""
model.py — Neural network architecture and loss functions.

Extracted verbatim from model_4.ipynb (Cell 3).
Parameterised so the loss function can be swapped via `use_asym_loss`.
"""

import tensorflow as tf
from tensorflow.keras.layers import (
    Input, Conv1D, MaxPooling1D,
    GlobalAveragePooling1D, GlobalMaxPooling1D,
    Dense, Concatenate, Dropout,
    BatchNormalization, DepthwiseConv1D,
)
from tensorflow.keras.models import Model

from config import FINAL_SPATIAL_STEPS


# ---------------------------------------------------------------------------
# Loss Functions
# ---------------------------------------------------------------------------

class AsymmetricHuberLoss(tf.keras.losses.Loss):
    """
    Penalises under-predictions (True > Predicted) heavily to counteract
    the compression effects of log1p target transformation on severe roads.
    """
    def __init__(self, delta=2.0, penalty_ratio=4.0, **kwargs):
        super().__init__(**kwargs)
        self.delta         = delta
        self.penalty_ratio = penalty_ratio

    def call(self, y_true, y_pred):
        error     = y_true - y_pred
        abs_error = tf.abs(error)

        quadratic  = tf.minimum(abs_error, self.delta)
        linear     = abs_error - quadratic
        huber_base = 0.5 * tf.square(quadratic) + self.delta * linear

        is_underpredicting = tf.cast(error > 0, tf.float32)
        weights = (is_underpredicting * self.penalty_ratio
                   + (1.0 - is_underpredicting) * 1.0)

        return tf.reduce_mean(weights * huber_base)

    def get_config(self):
        config = super().get_config()
        config.update({"delta": self.delta, "penalty_ratio": self.penalty_ratio})
        return config


# ---------------------------------------------------------------------------
# Model Builder
# ---------------------------------------------------------------------------

def build_iri_model(use_asym_loss=True):
    """
    Constructs the dual-input 1D-CNN + Dense network from model_4.ipynb.

    `use_asym_loss=False` switches to a standard Huber loss (Run 3 ablation).
    """
    # --- Branch 1: Spatial Feature Extraction (Raw IMU) ---
    input_raw = Input(shape=(FINAL_SPATIAL_STEPS, 6), name="raw_imu")

    x = DepthwiseConv1D(kernel_size=5, depth_multiplier=2,
                        activation='relu', padding='same')(input_raw)
    x = BatchNormalization()(x)
    x = MaxPooling1D(pool_size=2)(x)

    x = Conv1D(filters=48, kernel_size=5, activation='relu', padding='same')(x)
    x = BatchNormalization()(x)
    x = MaxPooling1D(pool_size=2)(x)

    x = Conv1D(filters=64, kernel_size=3, activation='relu', padding='same')(x)
    x = BatchNormalization()(x)

    avg_pool     = GlobalAveragePooling1D()(x)
    max_pool     = GlobalMaxPooling1D()(x)
    cnn_features = Concatenate(name="cnn_features")([avg_pool, max_pool])
    cnn_features = Dropout(0.3)(cnn_features)

    # --- Branch 2: Contextual Network (Extracted Statistics) ---
    input_ctx = Input(shape=(13,), name="context_stats")

    y = Dense(32, activation='relu')(input_ctx)
    y = BatchNormalization()(y)
    y = Dropout(0.2)(y)

    # --- Feature Fusion ---
    merged = Concatenate(name="fusion_layer")([cnn_features, y])

    z = Dense(64, activation='relu')(merged)
    z = Dropout(0.2)(z)
    z = Dense(32, activation='relu')(z)

    output_iri = Dense(1, activation='softplus', name="predicted_iri")(z)

    model = Model(inputs=[input_raw, input_ctx], outputs=output_iri)

    # --------------- Ablation point: loss function -------------------------
    if use_asym_loss:
        loss_fn = AsymmetricHuberLoss(delta=2.0, penalty_ratio=4.0)
    else:
        # Standard symmetric Huber loss (delta=2.0 keeps scale comparable)
        loss_fn = tf.keras.losses.Huber(delta=2.0)
    # -----------------------------------------------------------------------

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss=loss_fn,
        metrics=['mae', tf.keras.metrics.RootMeanSquaredError(name='rmse')],
    )

    return model
