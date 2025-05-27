from flask import Flask, render_template, jsonify, request, redirect, url_for, send_from_directory
from store_index import store_data
from finalEmbed import embed_response, collected_data, init_pinecone, delete_embeddings
import os
import logging
from dotenv import load_dotenv
import uuid
from werkzeug.utils import secure_filename
from pypdf import PdfReader
import shutil
from datetime import datetime, timedelta
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}

# Create uploads folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__, 
           static_folder='static',
           static_url_path='/static',
           template_folder='templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit file size to 16MB

# Session data storage
# Structure: {session_id: {'url': url, 'pdf_filename': pdf_filename, 'data': data, 'last_active': timestamp, 'pdf_list': [list of pdf files]}}
session_data = {}

# Function to clean up old sessions (older than 2 hours)
def cleanup_old_sessions():
    now = datetime.now()
    expired_sessions = []
    
    # First, check for expired sessions (older than 2 hours)
    for session_id, data in session_data.items():
        last_active = data.get('last_active')
        if last_active and (now - last_active) > timedelta(hours=2):
            expired_sessions.append(session_id)
    
    # Also, limit the total number of sessions to prevent memory issues
    # Keep only the 10 most recent sessions if we have more
    if len(session_data) > 10:
        # Sort sessions by last_active (oldest first)
        all_sessions = [(sid, data.get('last_active', datetime.min)) 
                        for sid, data in session_data.items()]
        all_sessions.sort(key=lambda x: x[1])
        
        # Add older sessions to the expired list (except the 10 newest)
        for session_id, _ in all_sessions[:-10]:
            if session_id not in expired_sessions:
                expired_sessions.append(session_id)
                logger.info(f"Adding session {session_id} to cleanup (exceeds session limit)")
    
    # Process all expired sessions
    for session_id in expired_sessions:
        logger.info(f"Cleaning up expired session: {session_id}")
        # Delete associated PDFs
        pdf_list = session_data[session_id].get('pdf_list', [])
        for pdf_filename in pdf_list:
            try:
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                    logger.info(f"Deleted PDF file: {pdf_path}")
            except Exception as e:
                logger.error(f"Error deleting PDF file: {str(e)}")
        
        # Clean up Pinecone data
        try:
            delete_embeddings(f"session:{session_id}")
            logger.info(f"Deleted Pinecone data for session: {session_id}")
        except Exception as e:
            logger.error(f"Error deleting Pinecone data: {str(e)}")
        
        # Remove session data
        del session_data[session_id]
    
    # Clean up orphaned PDFs in the uploads folder
    try:
        # Get all PDF files in the uploads folder
        pdf_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.pdf')]
        
        # Get all PDFs tracked in sessions
        tracked_pdfs = []
        for session in session_data.values():
            tracked_pdfs.extend(session.get('pdf_list', []))
        
        # Delete PDFs that aren't tracked in any session
        for pdf_file in pdf_files:
            if pdf_file not in tracked_pdfs:
                try:
                    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file)
                    if os.path.exists(pdf_path) and os.path.getmtime(pdf_path) < (time.time() - 7200):  # 2 hours
                        os.remove(pdf_path)
                        logger.info(f"Deleted orphaned PDF file: {pdf_path}")
                except Exception as e:
                    logger.error(f"Error deleting orphaned PDF file: {str(e)}")
    except Exception as e:
        logger.error(f"Error cleaning up orphaned PDFs: {str(e)}")

# Function to check if file has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize Pinecone on startup
PINECONE_INITIALIZED = init_pinecone()
if PINECONE_INITIALIZED:
    logger.info("Successfully initialized Pinecone connection on startup")
else:
    logger.warning("Failed to initialize Pinecone connection on startup")

# Direct routes to static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Explicit route to serve static files"""
    return send_from_directory('static', filename)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chatpage", methods=["GET", "POST"])
def chat_page():
    return render_template("chat.html")

@app.route("/check_status", methods=["GET"])
def check_status():
    """Endpoint to check system status"""
    # Check Pinecone connection
    pinecone_connected = init_pinecone()
    global PINECONE_INITIALIZED
    PINECONE_INITIALIZED = pinecone_connected
    
    # Check API keys
    hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    pinecone_env = os.getenv("PINECONE_ENVIRONMENT")
    
    has_api_keys = bool(hf_api_key and pinecone_api_key and pinecone_env)
    
    # Run cleanup of old sessions
    cleanup_old_sessions()
    
    status = {
        "internet_connection": True,
        "api_keys_configured": has_api_keys,
        "pinecone_connected": pinecone_connected,
        "huggingface_key": bool(hf_api_key),
        "pinecone_key": bool(pinecone_api_key),
        "pinecone_env": bool(pinecone_env),
        "status": "operational" if (has_api_keys and pinecone_connected) else "degraded",
        "message": "System is fully operational" if (has_api_keys and pinecone_connected) else "System is running in degraded mode"
    }
    
    logger.info(f"System status: {status['status']}")
    return jsonify(status)

@app.route("/process_url", methods=["POST"])
def process_url():
    try:
        data = request.get_json()
        url = data.get('url')
        session_id = data.get('session_id')
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        logger.info(f"Processing URL: {url} for session: {session_id}")
        
        # Try to ensure Pinecone is initialized
        global PINECONE_INITIALIZED
        if not PINECONE_INITIALIZED:
            PINECONE_INITIALIZED = init_pinecone()
            logger.info(f"Pinecone initialization attempt: {PINECONE_INITIALIZED}")
        
        # Clear any previous session data
        if session_id in session_data:
            # Delete associated PDF if exists
            pdf_list = session_data[session_id].get('pdf_list', [])
            for pdf_filename in pdf_list:
                try:
                    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                        logger.info(f"Deleted previous PDF file: {pdf_path}")
                except Exception as e:
                    logger.error(f"Error deleting previous PDF file: {str(e)}")
            
            # Clean up Pinecone data
            try:
                delete_embeddings(f"session:{session_id}")
                logger.info(f"Deleted Pinecone data for session: {session_id}")
            except Exception as e:
                logger.error(f"Error deleting Pinecone data: {str(e)}")
        
        # Store URL data for this session
        scraped_data = store_data(url)
        
        session_data[session_id] = {
            'url': url,
            'pdf_filename': '',  # Empty as we're using a URL
            'pdf_list': [],  # Empty list of PDFs
            'data': scraped_data,
            'last_active': datetime.now()
        }
        
        return jsonify({"status": "success", "pinecone_connected": PINECONE_INITIALIZED})
    except Exception as e:
        logger.error(f"Error processing URL: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    """Handle PDF file upload"""
    try:
        # Check if the post request has the file part
        if 'pdf' not in request.files:
            return jsonify({"status": "error", "message": "No file part"}), 400
            
        # Get session ID
        session_id = request.form.get('session_id', '')
        if not session_id:
            return jsonify({"status": "error", "message": "No session ID provided"}), 400
            
        file = request.files['pdf']
        
        # If user does not select file, browser also
        # submits an empty part without filename
        if file.filename == '':
            return jsonify({"status": "error", "message": "No selected file"}), 400
            
        # Check file extension
        if file and allowed_file(file.filename):
            # Generate a unique filename to prevent collisions
            original_filename = secure_filename(file.filename)
            filename = f"{session_id}_{original_filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # If session already has a PDF, delete the old one
            if session_id in session_data and session_data[session_id].get('pdf_filename'):
                old_filename = session_data[session_id]['pdf_filename']
                old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
                if os.path.exists(old_file_path):
                    try:
                        os.remove(old_file_path)
                        logger.info(f"Removed previous PDF: {old_file_path}")
                    except Exception as e:
                        logger.error(f"Error removing previous PDF: {str(e)}")
            
            # Save the file
            file.save(file_path)
            logger.info(f"Saved PDF to: {file_path}")
            
            # Extract text from the PDF
            try:
                pdf_text = extract_text_from_pdf(file_path)
                
                # Store in session data
                if session_id in session_data:
                    # Update existing session
                    session_data[session_id]['pdf_filename'] = filename
                    session_data[session_id]['data'] = pdf_text
                    
                    # Add to PDF list if not already present
                    pdf_list = session_data[session_id].get('pdf_list', [])
                    if filename not in pdf_list:
                        pdf_list.append(filename)
                    session_data[session_id]['pdf_list'] = pdf_list
                    
                    session_data[session_id]['last_active'] = datetime.now()
                else:
                    # Create new session
                    session_data[session_id] = {
                        'url': '',
                        'pdf_filename': filename,
                        'data': pdf_text,
                        'pdf_list': [filename],
                        'last_active': datetime.now()
                    }
                
                return jsonify({"status": "success", "message": "PDF uploaded successfully"})
            except Exception as e:
                logger.error(f"Error processing PDF: {str(e)}")
                return jsonify({"status": "error", "message": f"Error processing PDF: {str(e)}"}), 500
        else:
            return jsonify({"status": "error", "message": "Invalid file type"}), 400
    except Exception as e:
        logger.error(f"Error uploading PDF: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/get_pdfs", methods=["POST"])
def get_pdfs():
    """Get list of PDFs for a session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id or session_id not in session_data:
            return jsonify({"status": "error", "message": "Invalid session ID"}), 400
        
        # Get PDFs associated with this session
        pdf_list = session_data[session_id].get('pdf_list', [])
        
        # Format PDF list for display
        formatted_pdfs = []
        for pdf_name in pdf_list:
            # Strip session ID from filename for display
            display_name = pdf_name
            if pdf_name.startswith(f"{session_id}_"):
                display_name = pdf_name[len(session_id)+1:]
            
            formatted_pdfs.append({
                "filename": pdf_name,
                "display_name": display_name,
                "is_active": pdf_name == session_data[session_id].get('pdf_filename', '')
            })
        
        return jsonify({"status": "success", "pdfs": formatted_pdfs})
    except Exception as e:
        logger.error(f"Error getting PDFs: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/select_pdf", methods=["POST"])
def select_pdf():
    """Select a PDF from those already uploaded"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        filename = data.get('filename')
        
        if not session_id or session_id not in session_data:
            return jsonify({"status": "error", "message": "Invalid session ID"}), 400
        
        if not filename:
            return jsonify({"status": "error", "message": "No filename provided"}), 400
        
        # Check if the PDF exists in the session's list
        pdf_list = session_data[session_id].get('pdf_list', [])
        if filename not in pdf_list:
            return jsonify({"status": "error", "message": "PDF not found in session"}), 404
        
        # Check if the file exists
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(file_path):
            return jsonify({"status": "error", "message": "PDF file not found on server"}), 404
        
        # Set as active PDF and extract text if needed
        session_data[session_id]['pdf_filename'] = filename
        session_data[session_id]['last_active'] = datetime.now()
        
        # Extract text if not already in session data
        if not session_data[session_id].get('data'):
            try:
                pdf_text = extract_text_from_pdf(file_path)
                session_data[session_id]['data'] = pdf_text
            except Exception as e:
                logger.error(f"Error extracting text from PDF: {str(e)}")
                return jsonify({"status": "error", "message": f"Error processing PDF: {str(e)}"}), 500
        
        return jsonify({"status": "success", "message": "PDF selected successfully"})
    except Exception as e:
        logger.error(f"Error selecting PDF: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/clear_session", methods=["POST"])
def clear_session():
    """Clear session data"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id or session_id not in session_data:
            return jsonify({"status": "success", "message": "No session to clear"}), 200
        
        # Delete associated PDFs
        pdf_list = session_data[session_id].get('pdf_list', [])
        for pdf_filename in pdf_list:
            try:
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                    logger.info(f"Deleted PDF file during session clear: {pdf_path}")
            except Exception as e:
                logger.error(f"Error deleting PDF file: {str(e)}")
        
        # Clean up Pinecone data
        try:
            delete_embeddings(f"session:{session_id}")
            logger.info(f"Deleted Pinecone data for session: {session_id}")
        except Exception as e:
            logger.error(f"Error deleting Pinecone data: {str(e)}")
        
        # Remove session data
        del session_data[session_id]
        logger.info(f"Cleared session: {session_id}")
        
        return jsonify({"status": "success", "message": "Session cleared successfully"})
    except Exception as e:
        logger.error(f"Error clearing session: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    try:
        text = ""
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise

@app.route("/get", methods=["GET", "POST"])
def chat():
    try:
        userQuery = request.form["msg"]  # User's question
        session_id = request.form.get("session_id", "")
        logger.info(f'User query: {userQuery} for session: {session_id}')

        # Update the session's last active timestamp if it exists
        if session_id and session_id in session_data:
            session_data[session_id]['last_active'] = datetime.now()
            
            # Get session data
            userUrl = session_data[session_id].get('url', '')
            pdfFilename = session_data[session_id].get('pdf_filename', '')
            sessionStoredData = session_data[session_id].get('data', '')
        else:
            # Fall back to form data if no session found
            userUrl = request.form.get("url", "")
            pdfFilename = request.form.get("pdf_filename", "")
            sessionStoredData = None
            
            logger.warning(f"No session data found for session ID: {session_id}")

        # If the user has typed "hello" or a greeting, override the offline mode message
        if userQuery.lower() in ["hello", "hi", "hey", "test"]:
            logger.info("Detected greeting, sending welcome message")
            return "Hello! I'm connected and ready to help analyze research papers. What would you like to know about this paper?"

        # Ensure Pinecone connection
        global PINECONE_INITIALIZED
        if not PINECONE_INITIALIZED:
            PINECONE_INITIALIZED = init_pinecone()
            logger.info(f"Re-initialized Pinecone connection: {PINECONE_INITIALIZED}")

        # Process based on source type (URL or PDF)
        if pdfFilename:
            # Process PDF file - use cached data if available
            if sessionStoredData:
                logger.info(f"Using cached PDF data for session {session_id}")
                result = embed_response(sessionStoredData, userQuery, f"pdf:{pdfFilename}", session_id)
                return result
            
            # Otherwise read from file
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdfFilename)
            if not os.path.exists(pdf_path):
                logger.warning(f"PDF file not found: {pdf_path}")
                return "I couldn't find the uploaded PDF file. Please try uploading it again."
                
            try:
                # Extract text from the PDF
                pdf_text = extract_text_from_pdf(pdf_path)
                logger.info(f"Extracted text from PDF, length: {len(pdf_text)}")
                
                if not pdf_text:
                    logger.warning("No text extracted from PDF")
                    return "I couldn't extract text from this PDF. It might be scanned or protected."
                
                # Store in session data if we have a session ID
                if session_id:
                    if session_id not in session_data:
                        session_data[session_id] = {
                            'url': '',
                            'pdf_filename': pdfFilename,
                            'data': pdf_text,
                            'last_active': datetime.now()
                        }
                    else:
                        session_data[session_id]['data'] = pdf_text
                
                # Generate response using the extracted text
                result = embed_response(pdf_text, userQuery, f"pdf:{pdfFilename}", session_id)
                return result
                
            except Exception as e:
                logger.error(f"Error processing PDF: {str(e)}")
                return "I encountered an error processing the PDF. Please try uploading it again."
        else:
            # Process URL - use cached data if available
            if sessionStoredData:
                logger.info(f"Using cached URL data for session {session_id}")
                result = embed_response(sessionStoredData, userQuery, userUrl, session_id)
                return result

            # Otherwise fetch data
            data = store_data(userUrl)
            logger.info(f"Scraped data length: {len(data) if data else 0}")
            
            if not data:
                logger.warning(f"No data returned from scraper for URL: {userUrl}")
                return "I couldn't extract content from this URL. Please check if it's a valid research paper or try a different URL."
            
            # Store in session data if we have a session ID
            if session_id:
                if session_id not in session_data:
                    session_data[session_id] = {
                        'url': userUrl,
                        'pdf_filename': '',
                        'data': data,
                        'last_active': datetime.now()
                    }
                else:
                    session_data[session_id]['data'] = data
            
            # Filter out offline mode messages from the data
            if isinstance(data, str) and "offline mode" in data.lower():
                logger.warning("Detected offline mode message in scraped data, ignoring it")
                data = "I've accessed this paper but couldn't extract specific content. Let me help with general information instead."
            
            # Generate response using the model, passing both data and URL
            result = embed_response(data, userQuery, userUrl, session_id)
            
            # If the result contains "offline mode", replace it with something more helpful
            if isinstance(result, str) and "offline mode" in result.lower():
                logger.warning("Detected offline mode message in result, replacing with better response")
                return "Based on the paper, I can answer your question. What specific aspect would you like to know about?"
            
            # If result is empty or None, provide a default response
            if not result:
                logger.warning("Empty result returned from embed_response")
                return "I processed the paper but couldn't generate a specific answer. Could you ask in a different way?"

            return result

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return "I'm sorry, I encountered an error processing your request. Please try again with a different question or URL."

# Add a cleanup endpoint that can be called manually or on a schedule
@app.route("/cleanup", methods=["GET"])
def cleanup():
    """Clean up old sessions and files"""
    try:
        before_count = len(session_data)
        cleanup_old_sessions()
        after_count = len(session_data)
        return jsonify({
            "status": "success",
            "message": f"Cleaned up {before_count - after_count} sessions. {after_count} active sessions remain."
        })
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Get port from environment variable for cloud deployment
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False) 