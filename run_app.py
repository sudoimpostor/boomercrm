import sys
import os

# Point the runtime context to look at the local folder
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(0, BASE_DIR)

# Dynamic load execution of your loose text scripts
if __name__ == "__main__":
    import app_gui