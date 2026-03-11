import asyncio
import os
from core import RAGEngine, Config

async def seed():
    cfg = Config.from_env(db_path="./lancedb_data") # Match api.py default
    engine = RAGEngine(cfg)
    ws = "Main"
    
    # 1. Contract
    print("Seeding Contract...")
    contract_text = """
    SERVICE LEVEL AGREEMENT (SLA) - 2024
    
    1. Scope
    This agreement covers the delivery of widgets.
    
    2. Penalties
    The penalty for late delivery is exactly $5,000 per day, capped at $50,000 total.
    Exceptions apply for force majeure.
    """
    with open("contract.txt", "w") as f:
        f.write(contract_text)

    await engine.ingest_text_file(
        "contract.txt", 
        workspace_id=ws,
        source="contract.pdf", # Simulate PDF source
        title="Service Level Agreement 2024"
    )
    
    # 2. Mars Mission (Simulate PPTX text extraction)
    print("Seeding Mars Mission...")
    mars_text = """
    Mission to Mars: Strategic Overview
    
    Objectives:
    - Establish permanent base by 2035
    - Utilize in-situ resource utilization (ISRU) for water and fuel
    - Develop sustainable food production systems
    - Conduct geological surveys of Tharsis region
    
    Risks:
    - Radiation exposure during transit
    - Dust storms affecting solar power
    - Psychological isolation of crew
    """
    # Write to temp file to ingest
    with open("mars_temp.txt", "w") as f:
        f.write(mars_text)
        
    await engine.ingest_text_file(
        "mars_temp.txt",
        workspace_id=ws,
        source="mars_mission.pptx",
        title="Mars Mission Deck"
    )
    
    # 3. Project Alpha
    print("Seeding Project Alpha...")
    alpha_text = """
    Project Alpha Financial Overview
    
    Phase 1:
    - Budget: $1.5M
    - Timeline: Q1-Q2
    
    Phase 2:
    - Budget: $2.0M
    - Timeline: Q3-Q4
    
    Phase 3:
    - Budget: TBD
    """
    with open("project_alpha.txt", "w") as f:
        f.write(alpha_text)

    await engine.ingest_text_file(
        "project_alpha.txt",
        workspace_id=ws,
        source="project_alpha_notes.docx",
        title="Project Alpha Financials"
    )
    
    print("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed())
