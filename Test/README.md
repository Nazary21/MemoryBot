# Test Directory

This directory contains various test scripts for testing different components of the PykhBrain application.

## Test Files

### Component Tests

- **test_rule_manager.py**: Tests the RuleManager component, which is responsible for managing bot rules.
- **test_ai_handler.py**: Tests the AIResponseHandler component, which is responsible for generating AI responses.
- **test_memory_manager.py**: Tests the HybridMemoryManager component, which is responsible for storing and retrieving chat messages.

### Integration Tests

- **ai_response_test.py**: A comprehensive test script for testing the AI response generation with memory and rules.

### Database Tests

- **test_supabase.py**: Tests the Supabase database connection and operations.
- **verify_tables.py**: Verifies that all required tables exist in the Supabase database.
- **setup_database.py**: Sets up the necessary tables in the Supabase database.

## Running Tests

To run a test, use the following command:

```bash
python Test/test_file_name.py
```

For example:

```bash
python Test/test_rule_manager.py
```

## Test Results

Most tests will output their results to the console. Some tests may also create or modify files in the `memory` directory.

## Notes

- The tests are designed to work with both the Supabase database and the file-based fallback system.
- Some tests may fail if the Supabase database is not properly configured or if there are issues with the API keys.
- The tests are designed to be run in a development environment and may not be suitable for production use. 