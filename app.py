from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os
import uuid
import re
import logging
from datetime import datetime
import json
import random

# PDF and text processing
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("PyPDF2 not installed. PDF support disabled.")

# Simple in-memory storage for documents
documents = {}

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

class DocumentProcessor:
    """Handles document processing and text extraction"""
    
    @staticmethod
    def extract_text_from_pdf(file_path):
        """Extract text from PDF file"""
        if not PDF_SUPPORT:
            raise Exception("PDF support not available. Please install PyPDF2.")
        
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
        
        return text.strip()
    
    @staticmethod
    def extract_text_from_txt(file_path):
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, 'r', encoding='latin-1') as file:
                text = file.read()
        except Exception as e:
            logger.error(f"Error reading TXT file: {e}")
            raise Exception(f"Failed to read text file: {str(e)}")
        
        return text.strip()
    
    @staticmethod
    def split_into_paragraphs(text):
        """Split text into paragraphs for better processing"""
        paragraphs = []
        current_paragraph = []
        
        for line in text.split('\n'):
            line = line.strip()
            if line:
                current_paragraph.append(line)
            else:
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
        
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        return [p for p in paragraphs if len(p.strip()) > 20]  # Filter out very short paragraphs

class TextAnalyzer:
    """Handles text analysis and question answering"""
    
    @staticmethod
    def generate_summary(text, max_words=150):
        """Generate a summary of the text"""
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if not sentences:
            return "Unable to generate summary from this document."
        
        # Simple extractive summarization - take first few sentences and some from middle
        summary_sentences = []
        total_words = 0
        
        # Add first sentence
        if sentences:
            summary_sentences.append(sentences[0])
            total_words += len(sentences[0].split())
        
        # Add sentences from middle
        middle_start = len(sentences) // 3
        for i in range(middle_start, min(middle_start + 3, len(sentences))):
            if total_words >= max_words:
                break
            sentence = sentences[i]
            words_in_sentence = len(sentence.split())
            if total_words + words_in_sentence <= max_words:
                summary_sentences.append(sentence)
                total_words += words_in_sentence
        
        summary = '. '.join(summary_sentences)
        if not summary.endswith('.'):
            summary += '.'
        
        return summary
    
    @staticmethod
    def find_relevant_context(text, question, max_contexts=3):
        """Find relevant paragraphs for answering a question"""
        paragraphs = DocumentProcessor.split_into_paragraphs(text)
        
        # Extract meaningful words from question (excluding common stop words)
        stopwords = {'what', 'who', 'when', 'where', 'why', 'how', 'is', 'are', 'was', 'were', 'do', 'does', 'did', 'can', 'could', 'should', 'would', 'will', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'this', 'that', 'these', 'those'}
        
        question_words = set(re.findall(r'\b\w+\b', question.lower()))
        meaningful_question_words = question_words - stopwords
        
        scored_paragraphs = []
        for i, paragraph in enumerate(paragraphs):
            paragraph_words = set(re.findall(r'\b\w+\b', paragraph.lower()))
            
            # Calculate word overlap score
            word_overlap = len(meaningful_question_words.intersection(paragraph_words))
            
            # Calculate density score (percentage of question words found)
            density_score = word_overlap / len(meaningful_question_words) if meaningful_question_words else 0
            
            # Bonus for longer paragraphs (more context)
            length_bonus = min(len(paragraph.split()) / 100, 1.0)  # Cap at 1.0
            
            # Bonus for paragraphs with question-answering patterns
            pattern_bonus = 0
            paragraph_lower = paragraph.lower()
            if any(pattern in paragraph_lower for pattern in ['because', 'due to', 'reason', 'caused by']):
                pattern_bonus += 0.5
            if any(pattern in paragraph_lower for pattern in ['result', 'conclusion', 'shows', 'indicates', 'demonstrates']):
                pattern_bonus += 0.5
            if any(pattern in paragraph_lower for pattern in ['define', 'definition', 'means', 'refers to']):
                pattern_bonus += 0.5
            
            # Combined score
            total_score = word_overlap + (density_score * 2) + length_bonus + pattern_bonus
            
            if total_score > 0:
                scored_paragraphs.append((total_score, i, paragraph))
        
        # Sort by score and return top contexts
        scored_paragraphs.sort(reverse=True)
        return scored_paragraphs[:max_contexts]
    
    @staticmethod
    def answer_question(text, question):
        """Answer a question based on the document text"""
        relevant_contexts = TextAnalyzer.find_relevant_context(text, question)
        
        if not relevant_contexts:
            return {
                'answer': "I couldn't find relevant information to answer this question in the document.",
                'justification': "No relevant context found in the document for this question."
            }
        
        # Combine the most relevant contexts
        context_text = ' '.join([context[2] for context in relevant_contexts])
        
        # Generate answer based on context
        answer = TextAnalyzer.generate_contextual_answer(context_text, question)
        
        # Ensure the answer is not just repeating the question
        question_words = set(re.findall(r'\b\w+\b', question.lower()))
        answer_words = set(re.findall(r'\b\w+\b', answer.lower()))
        
        # If answer is too similar to question, try to get a different response
        if len(question_words.intersection(answer_words)) / len(question_words) > 0.8:
            # Try to get a different sentence from the context
            sentences = re.split(r'[.!?]+', context_text)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            
            for sentence in sentences:
                sentence_words = set(re.findall(r'\b\w+\b', sentence.lower()))
                if len(question_words.intersection(sentence_words)) / len(question_words) < 0.6:
                    answer = sentence
                    break
        
        # Clean up the answer
        answer = answer.strip()
        if not answer.endswith('.'):
            answer += '.'
        
        # Generate justification
        justification = f"Based on the document content, particularly from "
        if len(relevant_contexts) == 1:
            justification += f"paragraph {relevant_contexts[0][1] + 1}"
        else:
            justification += f"paragraphs {relevant_contexts[0][1] + 1}"
            if len(relevant_contexts) > 1:
                justification += f" and {len(relevant_contexts) - 1} other related sections"
        
        # Add snippet of most relevant content
        most_relevant_content = relevant_contexts[0][2][:150]
        justification += f". The relevant content includes: \"{most_relevant_content}...\""
        
        return {
            'answer': answer,
            'justification': justification
        }
    
    @staticmethod
    def generate_contextual_answer(context, question):
        """Generate an answer based on context and question"""
        # Clean up context and question
        context = context.strip()
        question_lower = question.lower()
        
        # Split context into sentences
        sentences = re.split(r'[.!?]+', context)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        if not sentences:
            return "The document contains relevant information but I cannot provide a specific answer."
        
        # Extract key question words (excluding common question words)
        question_stopwords = {'what', 'who', 'when', 'where', 'why', 'how', 'is', 'are', 'was', 'were', 'do', 'does', 'did', 'can', 'could', 'should', 'would', 'will', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        question_words = set(re.findall(r'\b\w+\b', question_lower))
        meaningful_question_words = question_words - question_stopwords
        
        # Score sentences based on relevance
        scored_sentences = []
        for sentence in sentences:
            sentence_words = set(re.findall(r'\b\w+\b', sentence.lower()))
            
            # Calculate relevance score
            word_overlap = len(meaningful_question_words.intersection(sentence_words))
            
            # Bonus for sentences that contain key question patterns
            pattern_bonus = 0
            if any(word in sentence.lower() for word in ['define', 'definition', 'means', 'refers to', 'is', 'are']):
                pattern_bonus += 1
            if any(word in sentence.lower() for word in ['because', 'due to', 'reason', 'caused by']):
                pattern_bonus += 1
            if any(word in sentence.lower() for word in ['result', 'conclusion', 'shows', 'indicates']):
                pattern_bonus += 1
            
            total_score = word_overlap + pattern_bonus
            
            if total_score > 0:
                scored_sentences.append((total_score, sentence))
        
        # Sort by score and get the best answer
        if scored_sentences:
            scored_sentences.sort(reverse=True)
            best_sentence = scored_sentences[0][1]
            
            # Try to improve the answer by combining related sentences
            if len(scored_sentences) > 1:
                # If the top sentences have similar scores, combine them
                top_score = scored_sentences[0][0]
                combined_answer = best_sentence
                
                for score, sentence in scored_sentences[1:3]:  # Check next 2 sentences
                    if score >= top_score * 0.7:  # If score is within 70% of top score
                        combined_answer += " " + sentence
                
                return combined_answer
            else:
                return best_sentence
        
        # If no good match found, try to find sentences that contain question keywords
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(word in sentence_lower for word in meaningful_question_words):
                return sentence
        
        # Last resort: return the first substantial sentence
        return sentences[0] if sentences else "I cannot find relevant information in the document to answer this question."
    
    @staticmethod
    def extract_key_concepts(text):
        """Extract key concepts, names, and important terms from the text"""
        # Split into sentences and clean
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # Find proper nouns (likely names, places, organizations)
        proper_nouns = set()
        for sentence in sentences:
            words = re.findall(r'\b[A-Z][a-z]+\b', sentence)
            proper_nouns.update(words)
        
        # Find numbers and dates
        numbers = re.findall(r'\b\d{4}\b|\b\d+\.\d+\b|\b\d+%\b', text)
        
        # Find quoted text
        quotes = re.findall(r'"([^"]*)"', text)
        
        # Find technical terms (words that appear frequently and are longer)
        words = re.findall(r'\b[a-zA-Z]{6,}\b', text.lower())
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get most frequent longer words
        technical_terms = [word for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]]
        
        return {
            'proper_nouns': list(proper_nouns)[:15],
            'numbers': numbers[:10],
            'quotes': quotes[:5],
            'technical_terms': technical_terms
        }
    
    @staticmethod
    def generate_challenge_questions(text):
        """Generate challenge questions from the document content"""
        paragraphs = DocumentProcessor.split_into_paragraphs(text)
        concepts = TextAnalyzer.extract_key_concepts(text)
        
        questions = []
        
        # If document is too short, generate basic questions
        if len(paragraphs) < 2:
            return [
                "What is the main topic discussed in this document?",
                "What are the key points mentioned in the text?",
                "What conclusions can be drawn from this document?"
            ]
        
        # Generate questions based on proper nouns (names, places, organizations)
        if concepts['proper_nouns']:
            selected_nouns = random.sample(concepts['proper_nouns'], min(3, len(concepts['proper_nouns'])))
            for noun in selected_nouns:
                questions.append(f"What role does {noun} play in the document?")
                questions.append(f"What information is provided about {noun}?")
        
        # Generate questions based on numbers and dates
        if concepts['numbers']:
            selected_numbers = random.sample(concepts['numbers'], min(2, len(concepts['numbers'])))
            for number in selected_numbers:
                questions.append(f"What is the significance of {number} mentioned in the document?")
        
        # Generate questions based on quotes
        if concepts['quotes']:
            selected_quotes = random.sample(concepts['quotes'], min(2, len(concepts['quotes'])))
            for quote in selected_quotes:
                if len(quote) > 20:  # Only use substantial quotes
                    questions.append(f"Who said or wrote: '{quote[:50]}...'?")
                    questions.append(f"What is the context of the quote: '{quote[:50]}...'?")
        
        # Generate questions based on technical terms
        if concepts['technical_terms']:
            selected_terms = random.sample(concepts['technical_terms'], min(3, len(concepts['technical_terms'])))
            for term in selected_terms:
                questions.append(f"How is the term '{term}' defined or explained in the document?")
                questions.append(f"What is the importance of '{term}' in the context of this document?")
        
        # Generate questions based on document structure
        if len(paragraphs) >= 3:
            # Questions about different sections
            questions.append("What is discussed in the opening section of the document?")
            questions.append("What are the main arguments presented in the middle sections?")
            questions.append("What conclusions are drawn in the final section?")
        
        # Generate analytical questions based on content
        questions.extend([
            "What is the author's main argument or thesis?",
            "What evidence does the author provide to support their claims?",
            "What are the key takeaways from this document?",
            "How does the author structure their argument?",
            "What examples or case studies are mentioned?",
            "What are the implications of the information presented?",
            "What questions does this document raise?",
            "How does this document relate to broader themes or issues?"
        ])
        
        # Remove duplicates and shuffle
        questions = list(set(questions))
        random.shuffle(questions)
        
        # Return a reasonable number of questions (5-8)
        return questions[:min(8, len(questions))] if questions else [
            "What is the main topic discussed in this document?",
            "What are the key points mentioned in the text?",
            "What conclusions can be drawn from this document?"
        ]
    
    @staticmethod
    def evaluate_answer(document_text, question, user_answer):
        """Evaluate user's answer against the document"""
        # Get the "correct" answer from the document
        correct_response = TextAnalyzer.answer_question(document_text, question)
        
        # Simple evaluation based on keyword matching
        user_words = set(re.findall(r'\b\w+\b', user_answer.lower()))
        correct_words = set(re.findall(r'\b\w+\b', correct_response['answer'].lower()))
        
        # Also check against the broader document context
        document_words = set(re.findall(r'\b\w+\b', document_text.lower()))
        
        # Calculate overlap with correct answer and document
        correct_overlap = len(user_words.intersection(correct_words))
        document_overlap = len(user_words.intersection(document_words))
        
        # Weight both overlaps
        total_correct_words = len(correct_words) if correct_words else 1
        total_document_words = len(document_words) if document_words else 1
        
        correct_score = correct_overlap / total_correct_words
        document_score = document_overlap / min(total_document_words, 100)  # Cap to avoid very low scores
        
        # Combined score
        score = (correct_score * 0.7) + (document_score * 0.3)
        
        # Generate feedback based on score
        if score > 0.7:
            feedback = "Excellent! Your answer aligns well with the document content and demonstrates good understanding."
        elif score > 0.5:
            feedback = "Good answer! You captured important points from the document. Consider including more specific details."
        elif score > 0.3:
            feedback = "Your answer shows some understanding but could be more comprehensive. Review the document for additional details."
        else:
            feedback = "Your answer needs improvement. Please refer to the document more closely and include relevant information."
        
        return {
            'feedback': feedback,
            'justification': correct_response['justification'],
            'score': score
        }

# Flask routes
@app.route('/')
def index():
    """Serve the main HTML page"""
    # Read the HTML file content (you'll need to save the frontend HTML as index.html)
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Smart Research Assistant</title>
        </head>
        <body>
            <h1>Smart Research Assistant</h1>
            <p>Please save the frontend HTML as 'index.html' in the same directory as this script.</p>
        </body>
        </html>
        """

@app.route('/upload', methods=['POST'])
def upload_document():
    """Handle document upload"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Validate file type
        if not file.filename.lower().endswith(('.pdf', '.txt')):
            return jsonify({'success': False, 'error': 'Only PDF and TXT files are supported'})
        
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Save file
        filename = f"{document_id}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract text based on file type
        try:
            if file.filename.lower().endswith('.pdf'):
                text = DocumentProcessor.extract_text_from_pdf(filepath)
            else:
                text = DocumentProcessor.extract_text_from_txt(filepath)
            
            if not text.strip():
                return jsonify({'success': False, 'error': 'No text could be extracted from the document'})
            
            # Generate summary
            summary = TextAnalyzer.generate_summary(text)
            
            # Store document data
            documents[document_id] = {
                'filename': file.filename,
                'filepath': filepath,
                'text': text,
                'summary': summary,
                'upload_time': datetime.now().isoformat()
            }
            
            logger.info(f"Document uploaded successfully: {document_id}")
            
            return jsonify({
                'success': True,
                'document_id': document_id,
                'summary': summary,
                'filename': file.filename
            })
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return jsonify({'success': False, 'error': f'Error processing document: {str(e)}'})
    
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return jsonify({'success': False, 'error': 'Upload failed'})

@app.route('/ask', methods=['POST'])
def ask_question():
    """Handle question answering"""
    try:
        data = request.get_json()
        document_id = data.get('document_id')
        question = data.get('question')
        
        if not document_id or not question:
            return jsonify({'success': False, 'error': 'Document ID and question are required'})
        
        if document_id not in documents:
            return jsonify({'success': False, 'error': 'Document not found'})
        
        document = documents[document_id]
        result = TextAnalyzer.answer_question(document['text'], question)
        
        logger.info(f"Question answered for document {document_id}")
        
        return jsonify({
            'success': True,
            'answer': result['answer'],
            'justification': result['justification']
        })
    
    except Exception as e:
        logger.error(f"Question answering error: {e}")
        return jsonify({'success': False, 'error': 'Failed to answer question'})

@app.route('/challenge', methods=['POST'])
def generate_challenge():
    """Generate challenge questions"""
    try:
        data = request.get_json()
        document_id = data.get('document_id')
        
        if not document_id:
            return jsonify({'success': False, 'error': 'Document ID is required'})
        
        if document_id not in documents:
            return jsonify({'success': False, 'error': 'Document not found'})
        
        document = documents[document_id]
        questions = TextAnalyzer.generate_challenge_questions(document['text'])
        
        logger.info(f"Challenge questions generated for document {document_id}")
        
        return jsonify({
            'success': True,
            'questions': questions
        })
    
    except Exception as e:
        logger.error(f"Challenge generation error: {e}")
        return jsonify({'success': False, 'error': 'Failed to generate challenge questions'})

@app.route('/evaluate', methods=['POST'])
def evaluate_answers():
    """Evaluate user answers"""
    try:
        data = request.get_json()
        document_id = data.get('document_id')
        questions = data.get('questions')
        answers = data.get('answers')
        
        if not document_id or not questions or not answers:
            return jsonify({'success': False, 'error': 'Document ID, questions, and answers are required'})
        
        if document_id not in documents:
            return jsonify({'success': False, 'error': 'Document not found'})
        
        if len(questions) != len(answers):
            return jsonify({'success': False, 'error': 'Number of questions and answers must match'})
        
        document = documents[document_id]
        feedback = []
        
        for i, (question, answer) in enumerate(zip(questions, answers)):
            evaluation = TextAnalyzer.evaluate_answer(document['text'], question, answer)
            feedback.append({
                'question_index': i,
                'user_answer': answer,
                'feedback': evaluation['feedback'],
                'justification': evaluation['justification'],
                'score': evaluation['score']
            })
        
        logger.info(f"Answers evaluated for document {document_id}")
        
        return jsonify({
            'success': True,
            'feedback': feedback
        })
    
    except Exception as e:
        logger.error(f"Answer evaluation error: {e}")
        return jsonify({'success': False, 'error': 'Failed to evaluate answers'})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'documents_count': len(documents)
    })

if __name__ == '__main__':
    print("Starting Smart Research Assistant...")
    print("PDF Support:", "Enabled" if PDF_SUPPORT else "Disabled (install PyPDF2 for PDF support)")
    print("Server will be available at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

    