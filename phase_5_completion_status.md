$ python3 scripts/test_ai_imports.py
🤖 AI Services Structure Validation
============================================================

📁 Testing File Structure...
==================================================
✅ src/services/ai/models.py
✅ src/services/ai/orchestrator.py
✅ src/services/ai/fallback.py
✅ src/services/ai/llm/base.py
✅ src/services/ai/llm/openai_service.py
✅ src/services/ai/llm/anthropic_service.py
✅ src/services/ai/llm/prompt_manager.py
✅ src/services/ai/nlp/intent_classifier.py
✅ src/services/ai/nlp/entity_extractor.py
✅ src/services/ai/nlp/sentiment_analyzer.py
✅ src/services/ai/nlp/emotion_detector.py
✅ src/services/ai/nlp/language_detector.py
✅ src/services/ai/knowledge/embeddings.py
✅ src/services/ai/knowledge/vector_store.py
✅ src/services/ai/knowledge/indexer.py
✅ src/services/ai/knowledge/retriever.py

🎉 All required AI service files exist!
🧪 Testing AI Services Imports...
==================================================
✅ AIServiceError imported successfully
✅ AI models module imported successfully
✅ AI orchestrator module imported successfully
✅ AI fallback module imported successfully
✅ LLM base module imported successfully
✅ OpenAI service module imported successfully
✅ Anthropic service module imported successfully
✅ Prompt manager module imported successfully
✅ Intent classifier module imported successfully
✅ Entity extractor module imported successfully
✅ Sentiment analyzer module imported successfully
✅ Emotion detector module imported successfully
✅ Language detector module imported successfully
✅ Embeddings service module imported successfully
✅ Vector store module imported successfully
✅ Knowledge indexer module imported successfully
✅ Knowledge retriever module imported successfully

🎉 All AI service modules imported successfully!
✅ Phase 5 AI/ML Services structure is valid

🔧 Testing Basic Functionality...
==================================================
✅ AIServiceError works correctly
✅ All modules are accessible

🎉 Basic functionality tests passed!

============================================================
📊 Test Results Summary:
  File Structure: ✅ PASS
  Module Imports: ✅ PASS
  Basic Functionality: ✅ PASS

🎉 All tests passed! Phase 5 AI/ML Services are ready!
📝 Note: Full functionality requires installing dependencies:
   pip install pydantic aiohttp asyncpg pinecone-client

