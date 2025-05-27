import pinecone
import os
import time
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def fix_pinecone_index():
    try:
        # Get Pinecone credentials
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pinecone_env = os.getenv("PINECONE_ENVIRONMENT")
        
        if not pinecone_api_key or not pinecone_env:
            logger.error("Pinecone API key or environment not set")
            return False
        
        logger.info(f"Initializing Pinecone with environment: {pinecone_env}")
        pc = pinecone.Pinecone(api_key=pinecone_api_key)
        
        # Index name for our application
        index_name = "research-assistant"
        
        # Check if index exists
        index_list = pc.list_indexes()
        index_names = [idx['name'] for idx in index_list] if index_list else []
        
        logger.info(f"Available Pinecone indexes: {index_names}")
        
        # Delete the index if it exists
        if index_name in index_names:
            logger.info(f"Deleting existing index: {index_name}")
            pc.delete_index(index_name)
            
            # Wait for deletion to complete
            logger.info("Waiting for index deletion to complete...")
            time.sleep(20)
            
            # Verify deletion
            new_index_list = pc.list_indexes()
            new_index_names = [idx['name'] for idx in new_index_list] if new_index_list else []
            
            if index_name in new_index_names:
                logger.error(f"Failed to delete index: {index_name}")
                return False
            else:
                logger.info(f"Successfully deleted index: {index_name}")
        
        # Create new index with correct dimensions
        try:
            logger.info(f"Creating new index: {index_name}")
            pc.create_index(
                name=index_name,
                dimension=384,  # Dimension for all-MiniLM-L6-v2 model
                metric="cosine",
                spec={"serverless": {"cloud": "aws", "region": "us-east-1"}}
            )
            
            # Wait for index creation to complete
            logger.info("Waiting for index creation to complete...")
            time.sleep(15)
            
            # Verify creation
            verify_index_list = pc.list_indexes()
            verify_index_names = [idx['name'] for idx in verify_index_list] if verify_index_list else []
            
            if index_name in verify_index_names:
                logger.info(f"Successfully created index: {index_name}")
                
                # Test connecting to the index
                try:
                    index = pc.Index(index_name)
                    logger.info("Successfully connected to index")
                    return True
                except Exception as e:
                    logger.error(f"Error connecting to index: {str(e)}")
                    return False
            else:
                logger.error(f"Failed to create index: {index_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error in fix_pinecone_index: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting Pinecone index fix process")
    success = fix_pinecone_index()
    
    if success:
        logger.info("Successfully fixed Pinecone index")
        print("✅ Pinecone index fixed successfully!")
    else:
        logger.error("Failed to fix Pinecone index")
        print("❌ Failed to fix Pinecone index, check logs for details") 