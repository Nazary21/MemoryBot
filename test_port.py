import os

# Get the PORT environment variable, default to 8000 if not set
port = os.environ.get('PORT', '8000')

# Print debug information
print(f"PORT environment variable: {port}")
print(f"PORT type: {type(port)}")

# Convert port to integer
port_int = int(port)
print(f"Converted PORT to integer: {port_int}")
print(f"PORT integer type: {type(port_int)}") 