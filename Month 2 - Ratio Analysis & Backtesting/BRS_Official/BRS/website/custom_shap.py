import shap
import numpy as np

# Override np.bool with bool
np.bool = bool

# Import TreeExplainer class from shap
from shap import TreeExplainer
