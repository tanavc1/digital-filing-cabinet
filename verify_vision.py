
import os
import shutil
import asyncio
import io
import time
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from main import Config, RAGEngine
from vision_analyzer import analyze_image

load_dotenv()

# Generate a synthetic image text
TEST_SECRET_CODE = "Omega-7799"
TEST_IMAGE_TEXT = f"TOP SECRET\nPROJECT OMEGA\nSECURITY CODE: {TEST_SECRET_CODE}"

def generate_test_image() -> bytes:
    """Generates a simple image with text using Pillow."""
    img = Image.new('RGB', (400, 200), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # Use default font or try to load one? Default is safer for CI.
    # To make text larger, proper font needed, but default might be too small.
    # Let's try to grab a truetype if available, or just scale.
    # For CI safety, we'll just draw the text multiple times or use default.
    # Pillow default font is very small.
    
    try:
        # Try a common linux/mac font
        font = ImageFont.truetype("Arial.ttf", 20)
    except IOError:
        try:
             font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except IOError:
             font = None # Default
    
    d.text((20, 50), TEST_IMAGE_TEXT, fill=(255, 0, 0), font=font)
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def setup_env():
    # clean db for isolation
    db_path = "./test_lancedb_vision"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    os.makedirs("sample_docs_vision", exist_ok=True)
    return Config.from_env(db_path=db_path)

async def run_test():
    print("--- Starting Vision Verification Test ---")
    
    # 0. Check Keys
    if not os.getenv("GEMINI_API_KEY"):
        print("SKIP: GEMINI_API_KEY not found.")
        return

    # 1. Setup
    cfg = setup_env()
    engine = RAGEngine(cfg)
    workspace_id = "VisionTest"

    # 2. Generate Image
    print("Generating synthetic image...")
    image_bytes = generate_test_image()
    print(f"Image generated ({len(image_bytes)} bytes).")

    # 3. Vision Analysis
    print("Analyzing with Gemini Vision...")
    try:
        # analyze_image takes bytes
        result = await asyncio.to_thread(analyze_image, image_bytes)
        print("Analysis complete.")
        print(f"Description preview: {result.description[:100]}...")
    except Exception as e:
        print(f"FAIL: Vision Analysis failed: {e}")
        exit(1)

    if result.confidence == 0:
        print("FAIL: Vision returned 0 confidence.")
        exit(1)

    # 4. Ingest (Mocking api.py logic)
    print("Ingesting result...")
    doc_title = "Secret Project Image"
    markdown_text = f"# {doc_title}\n\n**Image Type:** {result.image_type}\n\n## Analysis\n\n{result.description}\n"
    
    # Write to temp file for ingestion
    tmp_path = "sample_docs_vision/test_img.md"
    with open(tmp_path, "w") as f:
        f.write(markdown_text)

    await engine.ingest_text_file(tmp_path, title=doc_title, workspace_id=workspace_id)
    print("Ingestion complete.")

    # 5. Query
    print("Querying RAG...")
    query = "What is the security code for Project Omega?"
    resp = await engine.query(query, workspace_id=workspace_id)
    
    print(f"Answer: {resp['answer']}")
    
    # 6. Verify
    if TEST_SECRET_CODE in resp['answer'] or TEST_SECRET_CODE.replace("-", " ") in resp['answer']:
        print("PASS: Retrieved secret code correctly.")
    else:
        print("FAIL: Secret code not found in answer.")
        # Debug
        print(f"Full analysis text was: {result.description}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(run_test())
