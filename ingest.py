import logging
# pyrefly: ignore [missing-import]
from sentence_transformers import SentenceTransformer
from db import supabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize the embedding model
# all-MiniLM-L6-v2 produces 384-dimensional vectors
logger.info("Initializing SentenceTransformer model: all-MiniLM-L6-v2")
model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_and_store(text: str, source_url: str):
    """
    Generates an embedding for the given text and stores it in Supabase.
    """
    try:
        logger.info(f"Generating embedding for statement: {text[:50]}...")
        embedding = model.encode(text).tolist()

        data = {
            "content": text,
            "source_url": source_url,
            "embedding": embedding
        }

        logger.info("Inserting record into Supabase 'official_statements' table...")
        response = supabase.table("official_statements").insert(data).execute()
        
        if response.data:
            logger.info(f"Successfully stored statement. ID: {response.data[0]['id']}")
        else:
            logger.error("Failed to store statement: No data returned from Supabase.")
            
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}")

if __name__ == "__main__":
    # Mock Geopolitical Data (Indian Context)
    statements = [
        "India is a federal union comprising 28 states and 8 union territories.",
        "India is recognized as the world's largest democracy by population.",
        "According to the latest census, Kerala has the highest literacy rate among Indian states."
    ]

    logger.info(f"Starting batch ingestion of {len(statements)} statements...")
    
    for statement in statements:
        embed_and_store(statement, "https://en.wikipedia.org/wiki/India")
    
    logger.info("Ingestion pipeline test complete.")
