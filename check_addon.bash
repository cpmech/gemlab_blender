#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Test the Blender addon
/opt/blender/blender --background --python-expr "
import sys
import traceback

sys.path.insert(0, '$SCRIPT_DIR/src')

try:
    # Import the addon module (the __init__.py file)
    import __init__ as addon
    print('MODULE_IMPORT_OK')
    
    # Test registration
    addon.register()
    print('MODULE_REGISTER_OK')
    
    # Test unregistration
    addon.unregister()
    print('MODULE_UNREGISTER_OK')
    
except Exception as e:
    print('ERROR: Failed to test addon')
    traceback.print_exc()
    sys.exit(1)

print('ALL_TESTS_PASSED')
"
