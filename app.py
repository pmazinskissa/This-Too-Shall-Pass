from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, flash
import os
import sys
import traceback
from dotenv import load_dotenv
import tempfile
import uuid
import json
import codecs
import markdown
from flask_session import Session  # Import for server-side sessions
from utils.openai_helper import OpenAIHelper
from utils.summary_generator import SummaryGenerator
from utils.docx_exporter import DocxExporter

# Load environment variables
from dotenv import load_dotenv
import os

# Load .env file if it exists (development), otherwise use environment variables (production)
if os.path.exists('.env'):
    load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
if not app.secret_key:
    import secrets
    app.secret_key = secrets.token_hex(16)
    print("WARNING: Using a randomly generated secret key. Sessions will not persist across restarts.")

# Configure server-side session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(tempfile.gettempdir(), 'flask_session')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
Session(app)  # Initialize Flask-Session

app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB max upload (increased)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize components
openai_helper = OpenAIHelper(api_key=os.getenv("OPENAI_API_KEY"))
summary_generator = SummaryGenerator(openai_helper)
docx_exporter = DocxExporter()


@app.route('/')
def index():
    """Render the home page"""
    return render_template('index.html')


@app.route('/generate-summary', methods=['POST'])
def generate_summary():
    """Generate meeting summary from transcript text"""
    if 'transcript' not in request.form and 'transcript_file' not in request.files:
        return jsonify({'error': 'No transcript provided'}), 400

    try:
        # Get transcript text either from form field or uploaded file
        if 'transcript_file' in request.files and request.files['transcript_file'].filename:
            file = request.files['transcript_file']
            file_extension = os.path.splitext(file.filename)[1].lower()
            transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}{file_extension}")

            # Save the uploaded file
            file.save(transcript_path)
            print(f"File saved to {transcript_path}")
            print(f"File extension: {file_extension}")

            # Process based on file type
            transcript_text = None

            if file_extension == '.docx':
                # Handle Word documents
                try:
                    import docx
                    doc = docx.Document(transcript_path)
                    transcript_text = '\n\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
                    print(f"Successfully extracted text from DOCX file, {len(transcript_text)} characters")
                except Exception as e:
                    print(f"Error reading DOCX file: {str(e)}")
                    raise Exception(f"Could not extract text from Word document: {str(e)}")

            elif file_extension == '.txt' or file_extension == '.md' or file_extension == '.csv' or file_extension == '':
                # Handle text files with multiple encodings
                encodings_to_try = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'ascii']

                for encoding in encodings_to_try:
                    try:
                        with codecs.open(transcript_path, 'r', encoding=encoding) as f:
                            transcript_text = f.read()
                        print(f"Successfully read file with {encoding} encoding, {len(transcript_text)} characters")
                        break
                    except UnicodeDecodeError:
                        print(f"Failed to read with {encoding} encoding, trying next...")
                        continue

            else:
                # Unsupported file type
                raise Exception(f"Unsupported file type: {file_extension}. Please upload a .txt or .docx file.")

            # If all methods failed, raise an error
            if transcript_text is None:
                raise Exception("Could not extract text from the uploaded file. Please try pasting the text directly.")

            # Clean up the file after reading
            try:
                os.remove(transcript_path)
                print(f"Temporary file removed: {transcript_path}")
            except Exception as e:
                print(f"Warning: Could not remove temporary file: {str(e)}")

        else:
            transcript_text = request.form['transcript']
            print(f"Using text from form input, {len(transcript_text)} characters")

        # Validate transcript isn't too short
        if len(transcript_text) < 100:
            return jsonify({'error': 'Transcript is too short. Please provide a complete meeting transcript.'}), 400

        # Additional metadata from form
        meeting_title = request.form.get('meeting_title', 'Meeting Summary')
        meeting_date = request.form.get('meeting_date', '')
        meeting_duration = request.form.get('meeting_duration', '')
        persona_prompt = request.form.get('persona_prompt', '')  # New field
        context_prompt = request.form.get('context_prompt', '')  # New field

        print(f"Generating summary for: {meeting_title}")
        print(f"Transcript length: {len(transcript_text)} characters")
        print(f"First 100 characters of transcript: {transcript_text[:100]}...")
        print(f"Persona prompt: {persona_prompt}")
        print(f"Context prompt: {context_prompt}")

        # Generate summary
        summary = summary_generator.generate(
            transcript=transcript_text,
            title=meeting_title,
            date=meeting_date,
            duration=meeting_duration,
            persona_prompt=persona_prompt,  # New field
            context_prompt=context_prompt   # New field
        )

        # Validate summary has actual content by checking the markdown
        if 'markdown' in summary and not summary['markdown']:
            return jsonify({
                'error': 'The summary generation process did not extract meaningful content from your transcript. '
                         'Please try again with a different or more detailed transcript.'
            }), 400

        # Store in session for display and export
        session['summary'] = summary
        session['meeting_title'] = meeting_title
        session['meeting_date'] = meeting_date
        session['meeting_duration'] = meeting_duration
        session['persona_prompt'] = persona_prompt  # New field
        session['context_prompt'] = context_prompt  # New field

        return redirect(url_for('view_summary'))

    except UnicodeDecodeError as e:
        print(f"File encoding error: {str(e)}")
        return jsonify({'error': f'File encoding error: {str(e)}. Try saving your file as UTF-8 format.'}), 400
    except Exception as e:
        # Print detailed error for debugging
        print(f"Error generating summary: {str(e)}")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)

        # Provide a friendly error message
        error_message = str(e)
        if "context_length_exceeded" in error_message:
            error_message = "The transcript is too large for processing. Please try with a shorter transcript or break it into parts."
        elif "unsupported_parameter" in error_message or "unsupported_value" in error_message:
            error_message = "There was an issue with the AI model parameters. Please try again or contact support if the issue persists."

        return jsonify({'error': error_message}), 500


@app.route('/summary')
def view_summary():
    """Display the generated summary"""
    summary = session.get('summary')
    if not summary:
        return redirect(url_for('index'))

    meeting_title = session.get('meeting_title', 'Meeting Summary')
    meeting_date = session.get('meeting_date', '')
    meeting_duration = session.get('meeting_duration', '')
    persona_prompt = session.get('persona_prompt', '')  # New field
    context_prompt = session.get('context_prompt', '')  # New field

    # Get the raw markdown content
    raw_markdown = ""
    if 'markdown' in summary and summary['markdown']:
        raw_markdown = summary['markdown']

    # Convert markdown to HTML with improved processing
    try:
        # Add fenced_code extension to properly handle triple backticks
        markdown_html = markdown.markdown(
            raw_markdown,
            extensions=['tables', 'fenced_code']
        )
    except Exception as e:
        print(f"Error rendering markdown: {e}")
        # Fallback to structured data
        markdown_html = None

    return render_template(
        'summary.html',
        summary=summary,
        markdown_html=markdown_html,
        raw_markdown=raw_markdown,  # Pass raw markdown as well
        meeting_title=meeting_title,
        meeting_date=meeting_date,
        meeting_duration=meeting_duration,
        persona_prompt=persona_prompt,  # Pass new field to template
        context_prompt=context_prompt   # Pass new field to template
    )

@app.route('/export-docx')
def export_docx():
    """Export the summary as a Word document"""
    summary = session.get('summary')
    if not summary:
        return redirect(url_for('index'))

    meeting_title = session.get('meeting_title', 'Meeting Summary')
    meeting_date = session.get('meeting_date', '')
    meeting_duration = session.get('meeting_duration', '')

    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
    temp_filename = temp_file.name
    temp_file.close()

    try:
        # Generate the Word document
        docx_exporter.export(
            summary=summary,
            output_path=temp_filename,
            title=meeting_title,
            date=meeting_date,
            duration=meeting_duration
        )

        # Send the file
        return send_file(
            temp_filename,
            as_attachment=True,
            download_name=f"{meeting_title.replace(' ', '_')}_Summary.docx",
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        # If there's an error during export, report it
        print(f"Error exporting document: {str(e)}")
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        return jsonify({'error': f"Error exporting document: {str(e)}"}), 500
    finally:
        # Attempt to clean up the temp file in all cases
        try:
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)
        except:
            pass


@app.route('/debug-summary')
def debug_summary():
    """Debug endpoint to view the raw summary"""
    if not session.get('summary'):
        return redirect(url_for('index'))

    return jsonify(session.get('summary'))


if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_ENV", "development") == "development"
    app.run(debug=debug_mode, host='0.0.0.0')