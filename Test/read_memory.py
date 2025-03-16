#!/usr/bin/env python3
import os
import json
import sys

def read_memory_file(file_path):
    """Read a memory file and output its contents"""
    try:
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} does not exist")
            return False
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        print(json.dumps(data, indent=2))
        return True
    except Exception as e:
        print(f"Error reading file: {e}")
        return False

def list_directory(dir_path):
    """List the contents of a directory"""
    try:
        if not os.path.exists(dir_path):
            print(f"Error: Directory {dir_path} does not exist")
            return False
        
        files = os.listdir(dir_path)
        print(f"Contents of {dir_path}:")
        for file in files:
            full_path = os.path.join(dir_path, file)
            if os.path.isdir(full_path):
                print(f"  DIR: {file}")
            else:
                print(f"  FILE: {file} ({os.path.getsize(full_path)} bytes)")
        return True
    except Exception as e:
        print(f"Error listing directory: {e}")
        return False

if __name__ == "__main__":
    # Check if the volume mount point exists
    volume_path = os.environ.get('RAILWAY_VOLUME_MOUNT', '/data')
    memory_dir = os.path.join(volume_path, 'memory')
    account_dir = os.path.join(memory_dir, 'account_1')
    
    print(f"Volume path: {volume_path}")
    print(f"Memory directory: {memory_dir}")
    print(f"Account directory: {account_dir}")
    
    # List the root directory
    print("\nListing root directory:")
    list_directory('/')
    
    # List the volume directory
    print(f"\nListing volume directory ({volume_path}):")
    list_directory(volume_path)
    
    # List the memory directory if it exists
    if os.path.exists(memory_dir):
        print(f"\nListing memory directory ({memory_dir}):")
        list_directory(memory_dir)
        
        # List the account directory if it exists
        if os.path.exists(account_dir):
            print(f"\nListing account directory ({account_dir}):")
            list_directory(account_dir)
            
            # Read the short-term memory file if it exists
            short_term_file = os.path.join(account_dir, 'short_term.json')
            if os.path.exists(short_term_file):
                print(f"\nContents of short_term.json:")
                read_memory_file(short_term_file)
            else:
                print(f"\nError: short_term.json does not exist at {short_term_file}")
        else:
            print(f"\nError: Account directory {account_dir} does not exist")
    else:
        print(f"\nError: Memory directory {memory_dir} does not exist") 