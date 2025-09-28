#!/usr/bin/env python3
"""
Entry point for the Wedding Invitation System Flask application.
This file serves as the main entry point for deployment platforms like Render.
"""

import sys
import os

# Add the wedding_invitation_system directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
wedding_system_dir = os.path.join(current_dir, 'wedding_invitation_system')
sys.path.insert(0, wedding_system_dir)

# Change working directory to wedding_invitation_system to ensure relative paths work
os.chdir(wedding_system_dir)

# Import the Flask app from the wedding_invitation_system directory
# Use importlib to avoid circular import issues
import importlib.util
spec = importlib.util.spec_from_file_location("wedding_app", os.path.join(wedding_system_dir, "app.py"))
wedding_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wedding_app)

# Get the Flask app instance
app = wedding_app.app

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))