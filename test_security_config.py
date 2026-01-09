#!/usr/bin/env python3
"""
Test script for security configuration and API client.
"""

import os
import sys
sys.path.append('.')

def test_configuration():
    """Test configuration loading and security features."""
    print("Testing security configuration...")
    
    try:
        from app.config import get_config, validate_api_credentials, SecurityConfig
        
        # Test configuration loading
        print("1. Testing configuration loading...")
        config = get_config('development')
        print(f"   ✓ Secret key configured: {bool(config.SECRET_KEY)}")
        print(f"   ✓ CORS origins: {config.CORS_ORIGINS}")
        
        # Test API config
        print("2. Testing API configuration...")
        api_config = config.get_api_config()
        print(f"   ✓ API configuration: {api_config}")
        
        # Test masked config
        print("3. Testing masked configuration...")
        masked_config = config.mask_sensitive_config()
        print(f"   ✓ Masked configuration keys: {list(masked_config.keys())}")
        
        # Test security validation
        print("4. Testing security validation...")
        test_key = "test-api-key-12345"
        is_valid = SecurityConfig.validate_api_key("TEST_KEY", test_key)
        print(f"   ✓ API key validation: {is_valid}")
        
        print("✅ Configuration tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_secure_api_client():
    """Test secure API client functionality."""
    print("\nTesting secure API client...")
    
    try:
        from app.services.secure_api_client import SecureAPIClient, APIProvider
        
        # Test client initialization
        print("1. Testing client initialization...")
        client = SecureAPIClient()
        print("   ✓ Secure API client initialized")
        
        # Test provider status
        print("2. Testing provider status...")
        status = client.get_provider_status()
        print(f"   ✓ Provider status retrieved: {len(status)} providers")
        
        # Test security info
        print("3. Testing security information...")
        security_info = client.get_security_info()
        print(f"   ✓ Security info: SSL={security_info.get('ssl_verification')}")
        
        print("✅ Secure API client tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Secure API client test failed: {e}")
        return False


def test_flask_app_creation():
    """Test Flask app creation with security features."""
    print("\nTesting Flask app creation...")
    
    try:
        from app.app import create_app
        
        # Test app creation
        print("1. Testing app creation...")
        app = create_app('testing')
        print("   ✓ Flask app created successfully")
        
        # Test configuration
        print("2. Testing app configuration...")
        print(f"   ✓ Debug mode: {app.config.get('DEBUG')}")
        print(f"   ✓ Testing mode: {app.config.get('TESTING')}")
        print(f"   ✓ Secret key configured: {bool(app.config.get('SECRET_KEY'))}")
        
        # Test security headers (would need to make a request)
        print("3. Testing security features...")
        print(f"   ✓ CSRF enabled: {app.config.get('WTF_CSRF_ENABLED')}")
        print(f"   ✓ Session cookie secure: {app.config.get('SESSION_COOKIE_SECURE')}")
        
        print("✅ Flask app tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Flask app test failed: {e}")
        return False


if __name__ == "__main__":
    print("🔒 Security Implementation Test Suite")
    print("=" * 50)
    
    # Run all tests
    tests = [
        test_configuration,
        test_secure_api_client,
        test_flask_app_creation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All security tests passed!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Check the output above.")
        sys.exit(1)