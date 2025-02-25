import os
import sys

print("============ PORT HANDLING TEST ============")
print(f"Python version: {sys.version}")

# Test different PORT values
test_cases = [
    ('8000', 8000),                  # Normal case
    ('$PORT', 8000),                 # Literal $PORT
    ('', 8000),                      # Empty string
    ('invalid', 8000),               # Invalid value
    ('9999', 9999)                   # Different valid port
]

for input_value, expected_output in test_cases:
    # Set environment variable
    os.environ['PORT'] = input_value
    
    # Get the PORT environment variable
    port_str = os.environ.get('PORT', '8000')
    print(f"\nTest case: PORT='{input_value}'")
    print(f"Raw PORT value: '{port_str}'")
    
    # Handle special case where PORT is literally '$PORT'
    if port_str == '$PORT':
        print("Detected literal '$PORT' string - using default port 8000")
        port = 8000
    else:
        # Ensure PORT is a valid integer
        try:
            port = int(port_str)
            print(f"Converted PORT to integer: {port}")
        except ValueError:
            print(f"ERROR: Could not convert PORT value '{port_str}' to integer")
            print("Using default port 8000")
            port = 8000
    
    # Check if result matches expected output
    if port == expected_output:
        print(f"✅ PASS: Got expected port value {port}")
    else:
        print(f"❌ FAIL: Expected {expected_output}, got {port}")

print("\n============ TEST COMPLETE ============") 