"""Simple test script to validate AI services imports and basic structure."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all AI service modules can be imported."""
    print("🧪 Testing AI Services Imports...")
    print("=" * 50)
    
    # Test core exceptions
    try:
        from src.core.exceptions import AIServiceError
        print("✅ AIServiceError imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import AIServiceError: {e}")
        return False
    
    # Test AI models (without pydantic dependencies)
    try:
        # We'll test the basic structure without importing pydantic-dependent classes
        import src.services.ai.models
        print("✅ AI models module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import AI models: {e}")
        return False
    
    # Test orchestrator structure
    try:
        import src.services.ai.orchestrator
        print("✅ AI orchestrator module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import AI orchestrator: {e}")
        return False
    
    # Test fallback system
    try:
        import src.services.ai.fallback
        print("✅ AI fallback module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import AI fallback: {e}")
        return False
    
    # Test LLM services
    try:
        import src.services.ai.llm.base
        print("✅ LLM base module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import LLM base: {e}")
        return False
    
    try:
        import src.services.ai.llm.openai_service
        print("✅ OpenAI service module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import OpenAI service: {e}")
        return False
    
    try:
        import src.services.ai.llm.anthropic_service
        print("✅ Anthropic service module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Anthropic service: {e}")
        return False
    
    try:
        import src.services.ai.llm.prompt_manager
        print("✅ Prompt manager module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import prompt manager: {e}")
        return False
    
    # Test NLP services
    try:
        import src.services.ai.nlp.intent_classifier
        print("✅ Intent classifier module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import intent classifier: {e}")
        return False
    
    try:
        import src.services.ai.nlp.entity_extractor
        print("✅ Entity extractor module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import entity extractor: {e}")
        return False
    
    try:
        import src.services.ai.nlp.sentiment_analyzer
        print("✅ Sentiment analyzer module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import sentiment analyzer: {e}")
        return False
    
    try:
        import src.services.ai.nlp.emotion_detector
        print("✅ Emotion detector module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import emotion detector: {e}")
        return False
    
    try:
        import src.services.ai.nlp.language_detector
        print("✅ Language detector module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import language detector: {e}")
        return False
    
    # Test RAG services
    try:
        import src.services.ai.knowledge.embeddings
        print("✅ Embeddings service module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import embeddings service: {e}")
        return False
    
    try:
        import src.services.ai.knowledge.vector_store
        print("✅ Vector store module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import vector store: {e}")
        return False
    
    try:
        import src.services.ai.knowledge.indexer
        print("✅ Knowledge indexer module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import knowledge indexer: {e}")
        return False
    
    try:
        import src.services.ai.knowledge.retriever
        print("✅ Knowledge retriever module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import knowledge retriever: {e}")
        return False
    
    print("\n🎉 All AI service modules imported successfully!")
    print("✅ Phase 5 AI/ML Services structure is valid")
    return True

def test_file_structure():
    """Test that all required files exist."""
    print("\n📁 Testing File Structure...")
    print("=" * 50)
    
    required_files = [
        "src/services/ai/models.py",
        "src/services/ai/orchestrator.py",
        "src/services/ai/fallback.py",
        "src/services/ai/llm/base.py",
        "src/services/ai/llm/openai_service.py",
        "src/services/ai/llm/anthropic_service.py",
        "src/services/ai/llm/prompt_manager.py",
        "src/services/ai/nlp/intent_classifier.py",
        "src/services/ai/nlp/entity_extractor.py",
        "src/services/ai/nlp/sentiment_analyzer.py",
        "src/services/ai/nlp/emotion_detector.py",
        "src/services/ai/nlp/language_detector.py",
        "src/services/ai/knowledge/embeddings.py",
        "src/services/ai/knowledge/vector_store.py",
        "src/services/ai/knowledge/indexer.py",
        "src/services/ai/knowledge/retriever.py",
    ]
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    all_exist = True
    
    for file_path in required_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            all_exist = False
    
    if all_exist:
        print("\n🎉 All required AI service files exist!")
        return True
    else:
        print("\n❌ Some files are missing!")
        return False

def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    print("\n🔧 Testing Basic Functionality...")
    print("=" * 50)
    
    try:
        # Test AIServiceError
        from src.core.exceptions import AIServiceError
        error = AIServiceError("Test error")
        assert str(error) == "Test error"
        assert error.code == "AIServiceError"
        print("✅ AIServiceError works correctly")
        
        # Test that we can access the modules
        import src.services.ai.models
        import src.services.ai.orchestrator
        import src.services.ai.fallback
        print("✅ All modules are accessible")
        
        print("\n🎉 Basic functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("🤖 AI Services Structure Validation")
    print("=" * 60)
    
    # Run all tests
    structure_ok = test_file_structure()
    imports_ok = test_imports()
    functionality_ok = test_basic_functionality()
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"  File Structure: {'✅ PASS' if structure_ok else '❌ FAIL'}")
    print(f"  Module Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    print(f"  Basic Functionality: {'✅ PASS' if functionality_ok else '❌ FAIL'}")
    
    if structure_ok and imports_ok and functionality_ok:
        print("\n🎉 All tests passed! Phase 5 AI/ML Services are ready!")
        print("📝 Note: Full functionality requires installing dependencies:")
        print("   pip install pydantic aiohttp asyncpg pinecone-client")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)
