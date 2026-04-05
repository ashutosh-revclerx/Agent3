#!/usr/bin/env python3
"""
Connection Test Script — Verify All Components
Tests database connectivity, imports, and basic configuration
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

async def test_imports():
    """Test all critical imports"""
    print("\n📦 Testing Imports...")
    try:
        from main import app
        print("   ✅ FastAPI app imported")
        
        import db
        print("   ✅ Database module imported")
        
        from agents import (
            facilitator, insight_mining, prompt_coaching,
            poll_consensus, industry_benchmark, prioritisation_roi,
            deck_builder, scraping_agent, opportunity_generation
        )
        print("   ✅ All 9 agents imported")
        
        from gemini_client import gemini_json, gemini_text
        print("   ✅ Gemini client imported")
        
        from schemas import CompanyDNA, ParticipantProfile
        print("   ✅ Schemas imported")
        
        from seed_context import seed_session
        print("   ✅ Seed context imported")
        
        return True
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False

async def test_database():
    """Test database connection"""
    print("\n🗄️  Testing Database Connection...")
    try:
        import db
        from dotenv import load_dotenv
        import os
        
        # Load environment
        env_path = Path(__file__).parent / "backend" / ".env"
        load_dotenv(env_path)
        
        # Initialize database
        await db.init_db()
        print("   ✅ Database pool initialized")
        
        # Test basic query
        async with db.get_connection() as conn:
            await conn.execute("SELECT 1")
        print("   ✅ Database query executed successfully")
        
        # Close pool
        await db.close_db()
        print("   ✅ Database pool closed gracefully")
        
        return True
    except Exception as e:
        print(f"   ❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_fastapi():
    """Test FastAPI app configuration"""
    print("\n🚀 Testing FastAPI Configuration...")
    try:
        from main import app, sessions, participants, ws_connections
        print("   ✅ FastAPI app initialized")
        print(f"   ✅ In-memory stores configured (sessions, participants, ws_connections)")
        
        # Check routes exist
        routes = [route.path for route in app.routes]
        critical_routes = [
            "/session/create",
            "/participant/join",
            "/phase/context",
            "/health"
        ]
        
        for route in critical_routes:
            if any(route in r for r in routes):
                print(f"   ✅ Route {route} registered")
            else:
                print(f"   ⚠️  Route {route} not found")
        
        return True
    except Exception as e:
        print(f"   ❌ FastAPI test failed: {e}")
        return False

async def test_env():
    """Test environment configuration"""
    print("\n⚙️  Testing Environment Configuration...")
    try:
        from dotenv import load_dotenv
        import os
        
        env_path = Path(__file__).parent / "backend" / ".env"
        if not env_path.exists():
            print(f"   ⚠️  .env file not found at {env_path}")
            print(f"   📝 Please create .env from .env.example and add your API keys")
            return False
        
        load_dotenv(env_path)
        
        checks = {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
            "NEXUS_API_KEY": os.getenv("NEXUS_API_KEY"),
            "DB_USER": os.getenv("DB_USER", "copilot_user"),
            "DB_PASSWORD": os.getenv("DB_PASSWORD", "copilot_password"),
            "DB_HOST": os.getenv("DB_HOST", "localhost"),
            "DB_PORT": os.getenv("DB_PORT", "5432"),
            "DB_NAME": os.getenv("DB_NAME", "copilot_db"),
        }
        
        for key, value in checks.items():
            if value:
                masked = value[:8] + "..." if len(str(value)) > 11 else value
                if key in ["DB_PASSWORD"]:
                    masked = "***" * 5
                print(f"   ✅ {key}: {masked}")
            else:
                print(f"   ⚠️  {key}: Not configured")
        
        return True
    except Exception as e:
        print(f"   ❌ Environment test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🔗 AI Consulting Copilot — Connection Test")
    print("="*60)
    
    results = {}
    
    # Test imports (synchronous, no DB needed)
    results["imports"] = await test_imports()
    
    # Test environment
    results["environment"] = await test_env()
    
    # Test database (requires PostgreSQL running)
    results["database"] = await test_database()
    
    # Test FastAPI
    results["fastapi"] = await test_fastapi()
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Results Summary")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_flag in results.items():
        status = "✅ PASS" if passed_flag else "❌ FAIL"
        print(f"   {test_name.upper()}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All connections verified! Ready to start backend.")
        print("\n💡 Next step: Run the backend")
        print("   cd backend && python -m uvicorn main:app --reload --port 8000")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
