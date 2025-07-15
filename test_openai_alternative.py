"""
Alternative OpenAI Client Test - Bypass initialization issues
"""
import os
import sys

# Test without importing langchain packages first
print("🔧 Testing OpenAI without any langchain imports...")

try:
    # Clear any problematic modules
    modules_to_remove = [name for name in sys.modules.keys() if 'langchain' in name.lower()]
    for module in modules_to_remove:
        del sys.modules[module]
    
    # Import OpenAI fresh
    import openai
    from openai import OpenAI, AsyncOpenAI
    print(f"✓ OpenAI {openai.__version__} imported successfully")
    
    # Test creating client with explicit parameters only
    api_key = os.getenv('DEEPSEEK_API_KEY', 'test-key')
    base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    
    print(f"API Key: {api_key[:10]}..." if api_key else "No API key")
    print(f"Base URL: {base_url}")
    
    # Try creating client using different approaches
    print("\n1. Creating with explicit parameters...")
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=30,
            max_retries=3
        )
        print("✓ OpenAI client created successfully with full params")
        
        # Test a simple operation
        # Note: This might fail due to API key, but should not fail on initialization
        print("✓ Client object created, initialization successful")
        
    except Exception as e:
        print(f"❌ Failed with full params: {e}")
        
        # Try minimal params
        print("\n2. Creating with minimal parameters...")
        try:
            client = OpenAI(api_key=api_key)
            print("✓ OpenAI client created successfully with minimal params")
        except Exception as e2:
            print(f"❌ Failed with minimal params: {e2}")
            
            # Try without base_url
            print("\n3. Creating without base_url...")
            try:
                client = OpenAI(api_key=api_key)
                print("✓ OpenAI client created successfully without base_url")
            except Exception as e3:
                print(f"❌ Failed without base_url: {e3}")

except ImportError as e:
    print(f"❌ Import failed: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

print("\n✅ Alternative test complete")
