
import os
import logging
import torch
from sentence_transformers import CrossEncoder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

def test_rerank_load():
    logger.info("--- TEST 3: Auto device + low_cpu_mem_usage=False ---")
    try:
        model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2", 
            device=None, # Auto
            model_kwargs={
                "low_cpu_mem_usage": False
            }
        )
        logger.info(f"Model device: {model.model.device}")
        
        scores = model.predict([("query", "doc")])
        logger.info(f"Score: {scores}")
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    test_rerank_load()
