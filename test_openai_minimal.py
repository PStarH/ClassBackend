"""
Minimal OpenAI Client Test - Debug proxies issue
"""
import os

# Test raw OpenAI import and initialization
try:
    from openai import OpenAI, AsyncOpenAI
    print("✓ OpenAI imported successfully")
    
    # Check OpenAI version
    import openai
    print(f"✓ OpenAI version: {openai.__version__}")
    
    # Test with just api_key
    api_key = os.getenv('DEEPSEEK_API_KEY', 'test-key')
    print(f"✓ API Key length: {len(api_key) if api_key else 0}")
    
    print("\n🔧 Testing bare minimum OpenAI client...")
    try:
        client = OpenAI(api_key=api_key)
        print("✓ Basic OpenAI client created successfully")
    except Exception as e:
        print(f"❌ Basic OpenAI client failed: {e}")
        # Try with even more minimal approach
        try:
            client = OpenAI(api_key=api_key, timeout=None, max_retries=0)
            print("✓ Minimal OpenAI client with timeout/retries worked")
        except Exception as e2:
            print(f"❌ Even minimal client failed: {e2}")
    
    print("\n🔧 Testing AsyncOpenAI...")
    try:
        async_client = AsyncOpenAI(api_key=api_key)
        print("✓ Basic AsyncOpenAI client created successfully")
    except Exception as e:
        print(f"❌ Basic AsyncOpenAI client failed: {e}")
        
    print("\n🔧 Inspecting OpenAI class signature...")
    import inspect
    sig = inspect.signature(OpenAI.__init__)
    print(f"OpenAI.__init__ parameters: {list(sig.parameters.keys())}")
    
except ImportError as e:
    print(f"❌ Failed to import OpenAI: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

print("\n✅ Test complete")
