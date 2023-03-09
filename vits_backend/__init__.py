import sys
import os

# Add the path to your subfolder to the system path
subfolder = os.path.abspath(os.path.dirname(__file__))
sys.path.append(subfolder)

# Add the current directory to the system path
current_dir = os.path.abspath(os.getcwd())
sys.path.append(current_dir)

# Now you can import modules from the current directory and the subfolder
 