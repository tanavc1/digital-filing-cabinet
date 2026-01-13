
import os
import shutil
import uuid
from main import Config, RAGEngine, LanceStore, now_ts

def test_isolation():
    # Setup clean db
    db_path = "./test_lancedb_isolation"
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
    
    cfg = Config.from_env(db_path=db_path)
    engine = RAGEngine(cfg)
    
    # 1. Ingest into Workspace A ("Space")
    print("--- 1. Ingesting into Workspace 'Space' ---")
    doc_id_space = engine.ingest_text_file(
        "sample_docs/space_overview.txt", 
        workspace_id="Space",
        title="Space Overview"
    )
    print(f"Ingested doc {doc_id_space} into 'Space'")

    # 2. Ingest into Workspace B ("Rome")
    print("\n--- 2. Ingesting into Workspace 'Rome' ---")
    # We'll use the same file, but it should get a new ID effectively, 
    # but let's just use it to populate the DB.
    doc_id_rome = engine.ingest_text_file(
        "sample_docs/space_overview.txt", 
        workspace_id="Rome", 
        title="Rome Space Overview"
    )
    print(f"Ingested doc {doc_id_rome} into 'Rome'")

    # 3. Search Isolation
    print("\n--- 3. Testing Search Isolation ---")
    
    # Search in Space (Expect hits)
    res_space = engine.query("SpaceX", workspace_id="Space")
    print(f"Search 'SpaceX' in 'Space': Found {len(res_space['sources'])} sources")
    assert not res_space["abstained"], "Should find results in Space"

    # Search in Rome (Expect NO hits or hits only from Rome doc)
    # Since we ingested the same content, we expect hits from Rome doc, but NOT from Space doc.
    res_rome = engine.query("SpaceX", workspace_id="Rome")
    print(f"Search 'SpaceX' in 'Rome': Found {len(res_rome['sources'])} sources")
    
    for s in res_rome['sources']:
        # workspace_id is not in the output source dict by default in main.py
        # check doc_id matching instead
        assert s['doc_id'] == doc_id_rome, f"Leak detected! Found doc {s['doc_id']} (expected {doc_id_rome})"

    # 4. Deletion Isolation via ID Collision
    print("\n--- 4. Testing Deletion Isolation with ID Collision ---")
    
    # Manually insert two docs with SAME ID but different workspaces
    # (The system usually generates UUIDs, but we need to verify the protection against collision/malice)
    colliding_id = "COLLISION_TEST_ID"
    
    # Insert for Space
    engine.store.upsert_document({
        "doc_id": colliding_id,
        "workspace_id": "Space",
        "source": "manual",
        "uri": "",
        "title": "Collider Space",
        "created_at": now_ts(),
        "modified_at": now_ts(),
        "content_hash": "hash_space",
        "summary_text": "Space collision doc",
        "summary_model": "test",
        "summary_version": "v1"
    })
    
    # Insert for Rome
    engine.store.upsert_document({
        "doc_id": colliding_id,
        "workspace_id": "Rome",
        "source": "manual",
        "uri": "",
        "title": "Collider Rome",
        "created_at": now_ts(),
        "modified_at": now_ts(),
        "content_hash": "hash_rome",
        "summary_text": "Rome collision doc",
        "summary_model": "test",
        "summary_version": "v1"
    })
    
    # Verify both exist
    docs_space = engine.store.list_documents("Space")
    docs_rome = engine.store.list_documents("Rome")
    print(f"Docs in Space: {[d['doc_id'] for d in docs_space]}")
    print(f"Docs in Rome: {[d['doc_id'] for d in docs_rome]}")
    
    assert any(d['doc_id'] == colliding_id for d in docs_space)
    assert any(d['doc_id'] == colliding_id for d in docs_rome)
    
    # Delete from Space
    print(f"Deleting {colliding_id} from Space...")
    engine.delete_doc(colliding_id, workspace_id="Space")
    
    # Verify Space is gone, Rome remains
    docs_space_after = engine.store.list_documents("Space")
    docs_rome_after = engine.store.list_documents("Rome")
    
    print(f"Docs in Space after delete: {[d['doc_id'] for d in docs_space_after]}")
    print(f"Docs in Rome after delete: {[d['doc_id'] for d in docs_rome_after]}")

    assert not any(d['doc_id'] == colliding_id for d in docs_space_after), "Failed to delete from Space"
    assert any(d['doc_id'] == colliding_id for d in docs_rome_after), "Incorrectly deleted from Rome!"

    print("\nSUCCESS: Isolation verified.")

if __name__ == "__main__":
    try:
        test_isolation()
    except Exception as e:
        print(f"\nFAILED: {e}")
        exit(1)
