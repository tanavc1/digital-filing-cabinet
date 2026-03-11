import asyncio
import os
import shutil
import json
from core import Config, RAGEngine
from docling_loader import DoclingExtractor

# Setup environment
def setup_env():
    # different db for isolation
    db_path = "./test_lancedb_ingestion"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    return Config.from_env(db_path=db_path)

async def test_file(engine, extractor, file_path, expected_code, file_type):
    print(f"\n--- Testing {file_type} Ingestion ---")
    print(f"File: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"FAIL: File not found: {file_path}")
        return False

    try:
        # 1. Extraction (Simulate API / Docling)
        print("Extracting...")
        # Mirror API logic: Skip Docling for .txt
        if file_path.lower().endswith(".txt"):
            print("Skipping Docling for .txt...")
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            # Fake an extracted object for consistency
            class MockExtracted:
                def __init__(self, text, title):
                    self.text = text
                    self.title = title
            extracted = MockExtracted(text, os.path.basename(file_path))
        else:
            # Docling extract is sync
            extracted = extractor.extract(file_path)
            
        print(f"Extracted length: {len(extracted.text)} chars")
        
        # 2. Ingest
        print("Ingesting...")
        # write to temp txt file for ingestion
        tmp_txt = f"{file_path}.txt"
        with open(tmp_txt, "w") as f:
            f.write(extracted.text)
            
        doc_id = await engine.ingest_text_file(
            tmp_txt,
            title=extracted.title, 
            workspace_id="TestSpace"
        )
        print(f"Ingested Doc ID: {doc_id}")
        
        # 3. Query
        print("Querying...")
        q = f"What is the secret code for {file_type}?"
        res = await engine.query(q, workspace_id="TestSpace")
        print(f"Answer: {res['answer']}")
        
        if expected_code in res['answer']:
            print(f"PASS: Found code {expected_code}")
            return True
        else:
            print(f"FAIL: Code {expected_code} not found.")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def run_tests():
    cfg = setup_env()
    engine = RAGEngine(cfg)
    extractor = DoclingExtractor(enable_ocr=False) # OCR not needed for generated files
    
    results = []
    
    # PDF
    results.append(await test_file(engine, extractor, "sample_docs_real/fact.pdf", "1234", "PDF"))
    
    # DOCX
    results.append(await test_file(engine, extractor, "sample_docs_real/fact.docx", "5678", "DOCX"))
    
    # PPTX
    results.append(await test_file(engine, extractor, "sample_docs_real/fact.pptx", "9012", "PPTX"))
    
    # TXT (Docling can handle txt, but usually we skip it. Let's test docling on txt just to see)
    results.append(await test_file(engine, extractor, "sample_docs_real/fact.txt", "3456", "TXT"))

    print("\n" + "="*30)
    if all(results):
        print("ALL TESTS PASSED: Multi-format ingestion verified.")
    else:
        print("SOME TESTS FAILED.")
        exit(1)

if __name__ == "__main__":
    asyncio.run(run_tests())
