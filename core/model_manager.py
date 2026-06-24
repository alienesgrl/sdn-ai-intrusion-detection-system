import os
import glob

class ModelManager:
    def __init__(self, models_dir="models"):
        self.models_dir = models_dir
        if not os.path.exists(self.models_dir):
            os.makedirs(self.models_dir)

    def get_available_models(self):
        """
        Scan the models directory and return a list of model filenames (.pkl, .h5, .joblib).
        """
        models = []
        extensions = ('*.pkl', '*.h5', '*.joblib')
        for ext in extensions:
            pattern = os.path.join(self.models_dir, ext)
            for filepath in glob.glob(pattern):
                models.append(os.path.basename(filepath))
        return sorted(models)
