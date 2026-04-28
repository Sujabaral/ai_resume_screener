import pandas as pd
import os
from datetime import datetime

def export_to_excel(results, export_folder="exports"):
    os.makedirs(export_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(export_folder, f"resume_ranking_{timestamp}.xlsx")

    df = pd.DataFrame(results)
    df.to_excel(file_path, index=False)

    return file_path