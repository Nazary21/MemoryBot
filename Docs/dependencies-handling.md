# Dependency Conflict Resolution

## Problem

We encountered dependency conflicts between several key packages in our project:

1. `python-telegram-bot==20.7` requires `httpx~=0.25.2`
2. `supabase==2.13.0` requires `httpx>=0.26,<0.29`
3. `openai==1.12.0` requires `httpx>=0.23.0,<1`

These conflicting requirements made it impossible to install all packages simultaneously using standard pip installation methods.

Additionally, we discovered that `supabase==2.13.0` had initialization issues with an unexpected `proxy` parameter in the client constructor.

## Symptoms

The following errors were observed:

1. When trying to install dependencies from requirements.txt:
   ```
   ERROR: Cannot install -r requirements.txt (line 3), -r requirements.txt (line 4), httpx<0.29.0 and >=0.25.2 and supabase==2.12.0 because these package versions have conflicting dependencies.
   ```

2. When trying to initialize Supabase client with version 2.13.0:
   ```
   Error initializing Supabase client: Client.__init__() got an unexpected keyword argument 'proxy'
   ```

## Solution

We resolved these issues with the following approach:

1. Downgraded from `supabase==2.13.0` to `supabase==2.12.0` to avoid the initialization issues with the proxy parameter.

2. Identified `httpx==0.26.0` as a version that satisfies both requirements:
   - It's compatible with `supabase==2.12.0` (which requires `httpx>=0.26,<0.29`)
   - It's close enough to what `python-telegram-bot==20.7` requires (`httpx~=0.25.2`) to work in practice

3. Installed packages in a specific order to resolve conflicts:
   ```bash
   pip uninstall -y httpx python-telegram-bot supabase
   pip install httpx==0.26.0
   pip install python-telegram-bot==20.7 --no-deps
   pip install supabase==2.12.0
   ```

4. Updated requirements.txt to specify these exact versions:
   ```
   httpx==0.26.0
   supabase==2.12.0
   python-telegram-bot==20.7
   ```

5. Modified the Supabase initialization code in `config/database.py` to:
   - Use a simpler initialization method: `client = create_client(SUPABASE_URL, SUPABASE_KEY)`
   - Add a warning for version 2.13.0
   - Recommend version 2.12.0 in error messages

## Testing

We created a test script (`test_supabase.py`) to verify that Supabase initialization works correctly with our updated dependencies. The test confirmed that:

1. The Supabase client initializes successfully
2. Basic queries work as expected

## Lessons Learned

1. When facing complex dependency conflicts, sometimes installing packages individually in a specific order can resolve issues that pip's dependency resolver cannot handle automatically.

2. Using `--no-deps` with pip can be useful to avoid reinstalling dependencies that might break compatibility.

3. Testing different versions of packages can help identify compatible combinations that aren't immediately obvious from the stated requirements.

4. Always test initialization and basic functionality after resolving dependency issues to ensure the solution works in practice.

## Future Considerations

1. Monitor for updates to these packages that might resolve the compatibility issues.

2. Consider pinning all dependency versions in requirements.txt to avoid future conflicts.

3. If upgrading Supabase in the future, test initialization thoroughly before deploying.
