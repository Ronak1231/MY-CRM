import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from run import app  # Vercel's Python runtime auto-detects Flask/WSGI apps named 'app'