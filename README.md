# Smart Research Assistant 🧠

A Flask-based web application that provides intelligent question-answering capabilities for PDF and TXT documents. Upload your documents and get AI-powered insights through interactive Q&A sessions or challenge yourself with auto-generated questions.

## Features ✨

- **Document Upload**: Support for PDF and TXT files up to 16MB
- **Intelligent Text Processing**: Automatic text extraction and document summarization
- **Two Interaction Modes**:
  - **Ask Anything**: Ask free-form questions about your document
  - **Challenge Mode**: Test your understanding with AI-generated questions
- **Smart Question Answering**: Context-aware responses with justification
- **Answer Evaluation**: Automated feedback on challenge responses
- **Beautiful UI**: Modern, responsive design with academic theme
- **Real-time Processing**: Instant document analysis and question answering

## Screenshots 📸

The application features a warm, academic-themed interface with:
- Elegant document upload area with drag-and-drop support
- Interactive mode switching between "Ask Anything" and "Challenge Me"
- Real-time document summaries
- Detailed answer justifications
- Progressive feedback system

## Installation 🚀

### Prerequisites

- Python 3.7+
- pip package manager

### Setup

1. **Clone or download the project files**:
   ```bash
   # Ensure you have these files in your project directory:
   # - app.py
   # - index.html
   # - README.md (this file)
   ```

2. **Install required dependencies**:
   ```bash
   pip install flask flask-cors PyPDF2
   ```

3. **Create necessary directories**:
   ```bash
   mkdir uploads
   ```

4. **Run the application**:
   ```bash
   python app.py
   ```

5. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

## Usage Guide 📖

### 1. Upload a Document

- Click on the upload area or drag and drop a PDF/TXT file
- Supported formats: `.pdf`, `.txt`
- Maximum file size: 16MB
- The application will automatically extract text and generate a summary

### 2. Ask Anything Mode

- Switch to "Ask Anything" tab
- Type your question in the text area
- Click "Ask Question" to get an AI-generated answer
- Each answer includes:
  - Direct response to your question
  - Justification showing which parts of the document were used

### 3. Challenge Mode

- Switch to "Challenge Me" tab
- Click "Generate Challenge Questions" to create questions based on your document
- Answer each question in the provided text areas
- Click "Submit Answers" to get detailed feedback
- Feedback includes:
  - Evaluation of each answer
  - Justification from the document
  - Suggestions for improvement

## Technical Details 🔧

### Architecture

- **Backend**: Flask web framework with CORS support
- **Frontend**: Vanilla HTML/CSS/JavaScript with modern styling
- **Text Processing**: PyPDF2 for PDF extraction, custom algorithms for analysis
- **Storage**: In-memory document storage (documents persist during server session)

### Key Components

#### DocumentProcessor
- Handles PDF and TXT text extraction
- Splits documents into manageable paragraphs
- Supports multiple text encodings

#### TextAnalyzer
- Generates document summaries
- Finds relevant context for questions
- Creates contextual answers with justification
- Extracts key concepts (names, dates, technical terms)
- Generates challenge questions based on document content
- Evaluates user answers with scoring system

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the main HTML interface |
| `/upload` | POST | Handles document upload and processing |
| `/ask` | POST | Processes questions and returns answers |
| `/challenge` | POST | Generates challenge questions |
| `/evaluate` | POST | Evaluates user answers |
| `/health` | GET | Health check endpoint |

### File Structure

```
smart-research-assistant/
├── app.py              # Main Flask application
├── index.html          # Frontend interface
├── uploads/            # Document storage directory
└── README.md          # This file
```

## Configuration Options ⚙️

### Environment Variables

- `UPLOAD_FOLDER`: Directory for uploaded files (default: `uploads`)
- `MAX_CONTENT_LENGTH`: Maximum file size in bytes (default: 16MB)

### Customization

The application can be customized by modifying:

- **Text Analysis**: Adjust algorithms in `TextAnalyzer` class
- **UI Theme**: Modify CSS styles in `index.html`
- **Question Generation**: Customize logic in `generate_challenge_questions()`
- **Answer Evaluation**: Adjust scoring in `evaluate_answer()`

## Troubleshooting 🔍

### Common Issues

1. **PDF Support Disabled**
   ```bash
   # Install PyPDF2 if not already installed
   pip install PyPDF2
   ```

2. **File Upload Fails**
   - Check file size (must be under 16MB)
   - Ensure file format is PDF or TXT
   - Verify `uploads/` directory exists

3. **Text Extraction Issues**
   - Some PDFs may have embedded text that's difficult to extract
   - Try converting PDF to text format first
   - Ensure text encoding is UTF-8 or Latin-1

4. **Server Won't Start**
   - Check if port 5000 is available
   - Verify all dependencies are installed
   - Check Python version (requires 3.7+)

### Debug Mode

The application runs in debug mode by default. To disable:

```python
app.run(debug=False, host='0.0.0.0', port=5000)
```

## Limitations ⚠️

- **Document Storage**: Documents are stored in memory and lost when server restarts
- **Concurrent Users**: Basic in-memory storage may not handle high concurrency well
- **PDF Complexity**: Complex PDFs with images/tables may not extract text properly
- **Language Support**: Optimized for English text processing
- **File Size**: Limited to 16MB per document

## Future Enhancements 🚀

- Database integration for persistent storage
- Support for additional file formats (DOCX, RTF)
- Advanced NLP models for better question answering
- User authentication and document management
- Batch processing for multiple documents
- Export functionality for Q&A sessions
- Multi-language support
- Advanced search capabilities

## Contributing 🤝

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License 📄

This project is provided as-is for educational and research purposes. Feel free to modify and adapt according to your needs.

## Support 💬

For issues, questions, or contributions, please refer to the project documentation or create an issue in the project repository.

---

**Smart Research Assistant** - Making document analysis intelligent and interactive! 📚✨
