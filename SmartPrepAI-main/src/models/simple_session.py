import sqlite3
import json
from typing import Dict, List, Optional

class SimpleSessionManager:
    def __init__(self, db_path: str = "studyai.db"):
        self.db_path = db_path
        self.init_tables()
    
    def init_tables(self):
        """Initialize and update quiz sessions table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create base table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                topic TEXT NOT NULL,
                sub_topic TEXT,
                question_type TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                num_questions INTEGER NOT NULL,
                score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add new columns if they don't exist
        self._add_column_safe(cursor, 'quiz_sessions', 'questions_data', 'TEXT')
        self._add_column_safe(cursor, 'quiz_sessions', 'user_answers', 'TEXT')
        self._add_column_safe(cursor, 'quiz_sessions', 'results_data', 'TEXT')
        
        conn.commit()
        conn.close()
    
    def _add_column_safe(self, cursor, table_name: str, column_name: str, column_type: str):
        """Safely add column if it doesn't exist"""
        try:
            cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}')
        except sqlite3.OperationalError:
            pass  # Column already exists
    
    def save_quiz_session(self, user_id: int, quiz_data: Dict) -> int:
        """Save complete quiz session with all data for revision"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Use Row factory for safer access
            cursor = conn.cursor()
            
            # Always save with new format
            cursor.execute('''
                INSERT INTO quiz_sessions (
                    user_id, topic, sub_topic, question_type, difficulty, 
                    num_questions, score, questions_data, user_answers, results_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                int(user_id),
                str(quiz_data.get('topic', '')),
                str(quiz_data.get('sub_topic', '')),
                str(quiz_data.get('question_type', '')),
                str(quiz_data.get('difficulty', '')),
                int(quiz_data.get('num_questions', 0)),
                float(quiz_data.get('score', 0.0)),
                json.dumps(quiz_data.get('questions_data', [])),
                json.dumps(quiz_data.get('user_answers', [])),
                json.dumps(quiz_data.get('results_data', []))
            ])
            
            session_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return session_id
            
        except Exception as e:
            print(f"Session save error: {e}")
            return None
    
    def get_user_sessions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's quiz sessions for sidebar display with safe column access"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Use Row factory for safer access
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, topic, sub_topic, question_type, difficulty, 
                       num_questions, score, created_at
                FROM quiz_sessions 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', [int(user_id), int(limit)])
            
            sessions = []
            rows = cursor.fetchall()
            
            for row in rows:
                try:
                    # Safe access using row names
                    topic = row['topic'] if row['topic'] else "Quiz"
                    sub_topic = row['sub_topic'] if row['sub_topic'] else ""
                    
                    # Create display title
                    display_title = topic
                    if sub_topic:
                        display_title = f"{topic} - {sub_topic}"
                    
                    # Safe date formatting
                    created_at = row['created_at'] if row['created_at'] else ""
                    short_date = created_at[:10] if len(created_at) >= 10 else ""
                    
                    session_data = {
                        'id': row['id'],
                        'display_title': display_title,
                        'topic': topic,
                        'sub_topic': sub_topic,
                        'question_type': row['question_type'] if row['question_type'] else "Multiple Choice",
                        'difficulty': row['difficulty'] if row['difficulty'] else "Medium",
                        'num_questions': row['num_questions'] if row['num_questions'] else 1,
                        'score': float(row['score']) if row['score'] is not None else 0.0,
                        'created_at': created_at,
                        'short_date': short_date
                    }
                    
                    sessions.append(session_data)
                    
                except Exception as row_error:
                    print(f"Error processing row: {row_error}")
                    continue  # Skip this row and continue with others
            
            conn.close()
            print(f"Successfully retrieved {len(sessions)} sessions")  # Debug
            return sessions
            
        except Exception as e:
            print(f"Get sessions error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_complete_session(self, session_id) -> Optional[Dict]:
        """Get complete session data for revision view"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Use Row factory for safer access
            cursor = conn.cursor()
            
            # Handle session_id parameter properly
            if isinstance(session_id, (tuple, list)):
                session_id = session_id[0]
            session_id = int(session_id)
            
            cursor.execute('''
                SELECT * FROM quiz_sessions WHERE id = ?
            ''', [session_id])
            
            row = cursor.fetchone()
            
            if row:
                # Safe access to all columns
                result = {
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'topic': row['topic'] if row['topic'] else "General",
                    'sub_topic': row['sub_topic'] if row['sub_topic'] else "",
                    'question_type': row['question_type'] if row['question_type'] else "Multiple Choice",
                    'difficulty': row['difficulty'] if row['difficulty'] else "Medium",
                    'num_questions': row['num_questions'] if row['num_questions'] else 1,
                    'score': float(row['score']) if row['score'] is not None else 0.0,
                    'created_at': row['created_at'] if row['created_at'] else "",
                    'questions_data': [],
                    'user_answers': [],
                    'results_data': []
                }
                
                # Try to get detailed data if columns exist
                try:
                    if 'questions_data' in row.keys() and row['questions_data']:
                        result['questions_data'] = json.loads(row['questions_data'])
                    if 'user_answers' in row.keys() and row['user_answers']:
                        result['user_answers'] = json.loads(row['user_answers'])
                    if 'results_data' in row.keys() and row['results_data']:
                        result['results_data'] = json.loads(row['results_data'])
                except (json.JSONDecodeError, KeyError):
                    # Fallback to empty data if JSON parsing fails
                    pass
                
                conn.close()
                return result
            
            conn.close()
            return None
            
        except Exception as e:
            print(f"Get complete session error: {e}")
            return None
