from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEndpoint
from langchain_pinecone import PineconeVectorStore
import pinecone
import os
import time
import logging
import requests
import uuid
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Pinecone
def init_pinecone():
    try:
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pinecone_env = os.getenv("PINECONE_ENVIRONMENT")
        
        if not pinecone_api_key or not pinecone_env:
            logger.warning("Pinecone API key or environment not set")
            return False
            
        pc = pinecone.Pinecone(api_key=pinecone_api_key)
        
        # Check if index exists
        index_name = "research-assistant"
        
        # List all indexes to check if it exists
        index_list = pc.list_indexes()
        index_names = [idx['name'] for idx in index_list] if index_list else []
        
        logger.info(f"Available Pinecone indexes: {index_names}")
        
        # Check if we need to recreate the index (wrong dimensions)
        need_recreate = False
        if index_name in index_names:
            try:
                # Try to describe the index
                index_info = pc.describe_index(index_name)
                if hasattr(index_info, 'dimension'):
                    current_dimension = index_info.dimension
                    if current_dimension != 1024:  # We need 1024 for Mistral-Embed
                        logger.warning(f"Index has wrong dimension: {current_dimension}, needs 1024. Will recreate.")
                        need_recreate = True
                        # Delete the existing index
                        pc.delete_index(index_name)
                        logger.info(f"Deleted index {index_name} to recreate with correct dimensions")
                        # Wait for deletion to complete
                        time.sleep(15)
            except Exception as e:
                logger.error(f"Error checking index dimensions: {str(e)}")
        
        # Create index if it doesn't exist or needs recreation
        if index_name not in index_names or need_recreate:
            # Create index if it doesn't exist
            logger.info(f"Creating Pinecone index '{index_name}'")
            try:
                pc.create_index(
                    name=index_name,
                    dimension=1024,  # Dimension for Mistral-Embed model
                    metric="cosine",
                    spec={"serverless": {"cloud": "aws", "region": "us-east-1"}}
                )
                # Wait for index to be initialized
                time.sleep(10)
                logger.info(f"Successfully created Pinecone index '{index_name}'")
            except Exception as e:
                logger.error(f"Error creating Pinecone index: {str(e)}")
                # If creation fails, continue anyway - might be permissions
        
        try:
            index = pc.Index(index_name)
            logger.info("Successfully connected to Pinecone index")
            return True
        except Exception as e:
            logger.error(f"Error connecting to Pinecone index: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error initializing Pinecone: {str(e)}")
        return False

# Check if HuggingFace API is accessible
def check_huggingface_api():
    hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not hf_api_key:
        logger.warning("HuggingFace API key not set")
        return False
        
    try:
        headers = {"Authorization": f"Bearer {hf_api_key}"}
        response = requests.get(
            "https://api-inference.huggingface.co/models/google/flan-t5-small",
            headers=headers,
            timeout=5
        )
        if response.status_code < 400:
            logger.info("HuggingFace API is accessible")
            return True
        else:
            logger.warning(f"HuggingFace API returned status code {response.status_code}")
            return False
    except Exception as e:
        logger.warning(f"Failed to connect to HuggingFace API: {str(e)}")
        return False

# Store embeddings in Pinecone
def store_embeddings(text_chunks, url, session_id=None):
    try:
        # Initialize embeddings model - use a powerful model with 768 dimensions
        embeddings = HuggingFaceEmbeddings(
            model_name="mistralai/Mistral-Embed",  # High-quality embedding model
            model_kwargs={'device': 'cpu'}
        )
        
        # Initialize Pinecone
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pinecone_env = os.getenv("PINECONE_ENVIRONMENT")
        
        if not pinecone_api_key or not pinecone_env:
            logger.warning("Pinecone API key or environment not set")
            return False
            
        pc = pinecone.Pinecone(api_key=pinecone_api_key)
        index_name = "research-assistant"
        
        # Create documents with metadata
        documents = []
        source_id = f"session:{session_id}" if session_id else url
        
        # Generate a unique batch ID to identify this specific upload
        batch_id = str(uuid.uuid4())
        logger.info(f"Creating embeddings batch {batch_id} for source {source_id}")
        
        for i, chunk in enumerate(text_chunks):
            # Create a unique ID for each chunk
            chunk_id = f"{url.replace('/', '_')}_{i}"
            
            # Add metadata including session ID if available
            metadata = {
                "source": url,
                "chunk_id": i,
                "batch_id": batch_id,
                "source_id": source_id
            }
            
            # Add session identifier to metadata if available
            if session_id:
                metadata["session_id"] = session_id
            
            documents.append({
                "id": chunk_id,
                "text": chunk,
                "metadata": metadata
            })
        
        # If we have session_id, first try to delete any previous vectors for this session
        if session_id:
            try:
                # Get the index
                index = pc.Index(index_name)
                # Delete by session_id
                index.delete(filter={"session_id": {"$eq": session_id}})
                logger.info(f"Deleted previous embeddings for session: {session_id}")
            except Exception as e:
                logger.warning(f"Error deleting previous embeddings: {str(e)}")
        
        # Create vector store
        texts = [doc["text"] for doc in documents]
        metadatas = [doc["metadata"] for doc in documents]
        ids = [doc["id"] for doc in documents]
        
        # Store in Pinecone
        vector_store = PineconeVectorStore.from_texts(
            texts=texts,
            embedding=embeddings,
            ids=ids,
            metadatas=metadatas,
            index_name=index_name
        )
        
        logger.info(f"Successfully stored {len(texts)} chunks in Pinecone with source_id: {source_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error storing embeddings in Pinecone: {str(e)}")
        return False

# Simple placeholder to maintain API compatibility
def collected_data(data, userQuery):
    print(f'collected data: {data}')
    print(f'userQuery: {userQuery}')

def embed_response(data, userQuery, url=None, session_id=None):
    """Process paper data and generate a response to the user query"""
    # Check if data is empty or contains an error message
    if not data or data.startswith("Error") or data.startswith("Failed"):
        logger.warning(f"Received problematic content: {data[:100]}...")
        return process_query(userQuery)
    
    logger.info(f"Processing data of length {len(data)} characters")
    
    # Split text into manageable chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=300)
    chunks = text_splitter.split_text(data)
    
    if not chunks:
        logger.warning("No documents generated after text splitting")
        return process_query(userQuery)
    
    logger.info(f"Split text into {len(chunks)} chunks")
    
    # Store embeddings in Pinecone if URL is provided
    if url:
        store_success = store_embeddings(chunks, url, session_id)
        if store_success:
            logger.info("Successfully stored embeddings in Pinecone")
        else:
            logger.warning("Failed to store embeddings in Pinecone, continuing with direct processing")
    
    # Try to retrieve relevant context from Pinecone
    context = retrieve_from_pinecone(userQuery, url, session_id)
    
    # If no context from Pinecone, use the first few chunks
    if not context:
        logger.info("Using direct chunks as context")
        context = "\n\n".join(chunks[:5])
    
    return generate_response(userQuery, context)

def retrieve_from_pinecone(query, url=None, session_id=None):
    """Retrieve relevant context from Pinecone"""
    try:
        # Initialize embeddings model - use a powerful model with 768 dimensions
        embeddings = HuggingFaceEmbeddings(
            model_name="mistralai/Mistral-Embed",  # High-quality embedding model
            model_kwargs={'device': 'cpu'}
        )
        
        # Initialize Pinecone
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pinecone_env = os.getenv("PINECONE_ENVIRONMENT")
        
        if not pinecone_api_key or not pinecone_env:
            logger.warning("Pinecone API key or environment not set")
            return None
        
        # Connect to the index
        pc = pinecone.Pinecone(api_key=pinecone_api_key)
        index_name = "research-assistant"
        
        try:
            # Create vector store from existing index
            vector_store = PineconeVectorStore(
                index_name=index_name,
                embedding=embeddings
            )
            
            # Query params
            filter_dict = None
            
            # Set up filter based on available information
            if session_id:
                filter_dict = {"session_id": session_id}
            elif url:
                filter_dict = {"source": url}
            
            # Retrieve more documents (10 instead of 5) for better context
            docs = vector_store.similarity_search(
                query=query,
                k=10,
                filter=filter_dict
            )
            
            if docs:
                logger.info(f"Retrieved {len(docs)} documents from Pinecone")
                
                # Process and merge the documents into a coherent context
                all_content = [doc.page_content for doc in docs]
                
                # Further formatting to make the content more readable
                formatted_content = "\n\n".join(all_content)
                
                # Extract specific information if certain keywords are in the query
                if any(keyword in query.lower() for keyword in ["author", "who wrote", "researcher"]):
                    # Try to find author information more aggressively
                    for doc in docs:
                        content = doc.page_content.lower()
                        if "author" in content or "authors" in content or "written by" in content:
                            logger.info("Found potential author information")
                            return doc.page_content + "\n\n" + formatted_content
                
                return formatted_content
            else:
                logger.warning("No documents retrieved from Pinecone")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving from Pinecone: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"Error in retrieve_from_pinecone: {str(e)}")
        return None

def clean_response(response):
    """Clean up the response from the model to make it more presentable"""
    # Remove the prompt repetition that often appears in GPT-2 responses
    if "Answer:" in response:
        response = response.split("Answer:")[1].strip()
    
    # Limit response to first 3 sentences or 250 characters
    sentences = response.split('.')
    cleaned = '.'.join(sentences[:3]) if len(sentences) > 3 else response
    
    # If still too long, truncate
    if len(cleaned) > 250:
        cleaned = cleaned[:250] + "..."
        
    return cleaned

def generate_response(query, context=None):
    """Generate a response using HuggingFace models"""
    try:
        # Use HuggingFace's text generation model
        hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not hf_api_key:
            return "API key not configured. Please check your environment settings."
            
        # Use a more direct generation approach for simple questions
        headers = {"Authorization": f"Bearer {hf_api_key}"}
        
        if context:
            # Allow for more context to improve comprehension
            limited_context = context[:1000] if len(context) > 1000 else context
            
            # Format prompt for Mistral model
            prompt = f"""<s>[INST] You are a helpful AI research assistant named Samy. You were developed by Tenzin, Tatwansh and Praveen who are students at NSUT (Netaji Subhas University of Technology).

Use the following research paper extract to answer the question. Keep your answer under 3 sentences and be concise. If you don't know the answer, say you don't know instead of making something up.

Research paper extract: {limited_context}

Question: {query} [/INST]"""
            
            # Direct API call with Mistral-7B model
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 150,
                    "temperature": 0.3,
                    "top_p": 0.95
                }
            }
            
            try:
                logger.info(f"Sending direct query to HuggingFace API with context (Mistral model)")
                response = requests.post(
                    "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()[0]["generated_text"]
                    # Clean up the response - extract just the assistant's reply
                    result = result.split("[/INST]")[-1].strip()
                    return result
                else:
                    logger.error(f"HuggingFace API error: {response.status_code}, {response.text}")
                    return process_query(query)
            except Exception as e:
                logger.error(f"Error calling HuggingFace with context: {str(e)}")
                return process_query(query)
        else:
            return process_query(query)
            
    except Exception as e:
        logger.error(f"Error in generate_response: {str(e)}")
        return f"I encountered an error processing your request. Please try again with a different question or paper."

def process_query(query):
    """Process a query without paper context"""
    try:
        hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
        if not hf_api_key:
            return "API key not configured. Please check your environment settings."
            
        # Direct API call to avoid LangChain issues
        headers = {"Authorization": f"Bearer {hf_api_key}"}
        
        # Format prompt for Mistral model
        prompt = f"""<s>[INST] You are a helpful AI research assistant named Samy. You were developed by Tenzin, Tatwansh and Praveen who are students at NSUT (Netaji Subhas University of Technology).

Answer this question concisely in 2-3 sentences. If you don't know the answer, say you don't know.

Question: {query} [/INST]"""
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 150,
                "temperature": 0.3,
                "top_p": 0.95
            }
        }
        
        try:
            logger.info("Sending direct query to HuggingFace API (Mistral model)")
            response = requests.post(
                "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()[0]["generated_text"]
                # Clean up the response - extract just the assistant's reply
                result = result.split("[/INST]")[-1].strip()
                return result
            else:
                logger.error(f"HuggingFace API error: {response.status_code}, {response.text}")
                return f"I couldn't process your request. Please try a different question."
        except Exception as e:
            logger.error(f"Error calling HuggingFace for general query: {str(e)}")
            return f"I'm sorry, I couldn't process your request. Please try a different question."
    
    except Exception as e:
        logger.error(f"Error in process_query: {str(e)}")
        return f"I encountered an error processing your request. Please try again with a different question."

def delete_embeddings(source_identifier):
    """Delete embeddings from Pinecone based on source identifier"""
    try:
        # Initialize Pinecone
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pinecone_env = os.getenv("PINECONE_ENVIRONMENT")
        
        if not pinecone_api_key or not pinecone_env:
            logger.warning("Pinecone API key or environment not set")
            return False
            
        pc = pinecone.Pinecone(api_key=pinecone_api_key)
        index_name = "research-assistant"
        
        try:
            # Get the index
            index = pc.Index(index_name)
            
            # Check if this is a session identifier
            if source_identifier.startswith("session:"):
                # Use the session_id field for filtering when it's a session
                session_id = source_identifier.replace("session:", "")
                logger.info(f"Deleting by session_id: {session_id}")
                index.delete(filter={"session_id": {"$eq": session_id}})
            else:
                # Use source field for non-session identifiers
                logger.info(f"Deleting by source: {source_identifier}")
                index.delete(filter={"source": {"$eq": source_identifier}})
            
            logger.info(f"Successfully deleted embeddings for identifier: {source_identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting from Pinecone index: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Error connecting to Pinecone: {str(e)}")
        return False




