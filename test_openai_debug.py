#!/usr/bin/env python
"""
Quick test to isolate the OpenAI client issue
"""
import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

def test_openai_client():
    """Test OpenAI client initialization directly"""
    print("🔧 Testing OpenAI Client Initialization")
    
    try:
        from llm.core.client import llm_factory
        from llm.core.config import LLMConfig
        
        print(f"✓ API Key configured: {bool(LLMConfig.API_KEY)}")
        print(f"✓ Base URL: {LLMConfig.BASE_URL}")
        print(f"✓ Model: {LLMConfig.MODEL_NAME}")
        
        # Test basic client
        if llm_factory.is_available():
            print("✓ LLM Factory reports available")
            
            try:
                client = llm_factory.get_client()
                print("✓ OpenAI client initialized successfully")
            except Exception as e:
                print(f"❌ OpenAI client failed: {e}")
                
            try:
                async_client = llm_factory.get_async_client()
                print("✓ Async OpenAI client initialized successfully")
            except Exception as e:
                print(f"❌ Async OpenAI client failed: {e}")
        else:
            print("❌ LLM Factory not available")
            
    except Exception as e:
        print(f"❌ General error: {e}")
        import traceback
        traceback.print_exc()

def test_langchain_init():
    """Test LangChain initialization separately"""
    print("\n🔗 Testing LangChain Initialization")
    
    try:
        from langchain_openai import OpenAI as LangChainOpenAI
        from llm.core.config import LLMConfig
        
        if not LLMConfig.API_KEY:
            print("⚠️ No API key, skipping LangChain test")
            return
            
        # Test different initialization approaches
        approaches = [
            ("Modern syntax", {
                'api_key': LLMConfig.API_KEY,
                'base_url': LLMConfig.BASE_URL,
                'model_name': LLMConfig.MODEL_NAME,
                'temperature': LLMConfig.TEMPERATURE
            }),
            ("Legacy syntax", {
                'openai_api_key': LLMConfig.API_KEY,
                'model_name': LLMConfig.MODEL_NAME,
                'temperature': LLMConfig.TEMPERATURE
            }),
            ("Minimal syntax", {
                'openai_api_key': LLMConfig.API_KEY
            })
        ]
        
        for name, kwargs in approaches:
            try:
                llm = LangChainOpenAI(**kwargs)
                print(f"✓ {name} worked")
                break
            except Exception as e:
                print(f"❌ {name} failed: {e}")
                
    except ImportError as e:
        print(f"⚠️ LangChain not available: {e}")
    except Exception as e:
        print(f"❌ LangChain test error: {e}")

def test_service_init():
    """Test service initialization"""
    print("\n🤖 Testing Service Initialization")
    
    try:
        from llm.services.advisor_service import get_advisor_service
        
        service = get_advisor_service()
        print(f"✓ Advisor service initialized: {service.is_available()}")
        
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 OpenAI Client Diagnostic Test\n")
    test_openai_client()
    test_langchain_init()
    test_service_init()
    print("\n✅ Diagnostic complete")
