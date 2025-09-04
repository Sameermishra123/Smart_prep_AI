import streamlit as st
import sqlite3
import hashlib
from typing import Optional, Dict

class AuthManager:
    def __init__(self, db_path: str = "studyai.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                total_quizzes INTEGER DEFAULT 0,
                total_score REAL DEFAULT 0.0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return self.hash_password(password) == hashed
    
    def register_user(self, username: str, email: str, password: str) -> bool:
        """Register a new user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            password_hash = self.hash_password(password)
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Registration error: {e}")
            return False
    
    def login_user(self, username: str, password: str) -> Optional[Dict]:
        """Login user and return user data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Use row factory to get dictionary-like access
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id, username, email, password_hash, total_quizzes, total_score FROM users WHERE username = ?",
                (username,)
            )
            
            user_row = cursor.fetchone()
            
            if user_row:
                # Access by column name instead of index
                stored_password_hash = user_row['password_hash']
                
                if self.verify_password(password, stored_password_hash):
                    user_data = {
                        'id': user_row['id'],
                        'username': user_row['username'],
                        'email': user_row['email'],
                        'total_quizzes': user_row['total_quizzes'] if user_row['total_quizzes'] else 0,
                        'total_score': user_row['total_score'] if user_row['total_score'] else 0.0
                    }
                    
                    conn.close()
                    return user_data
            
            conn.close()
            return None
            
        except Exception as e:
            print(f"Login error: {e}")
            return None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return 'user' in st.session_state and st.session_state.user is not None
    
    def get_current_user(self) -> Optional[Dict]:
        """Get current logged in user"""
        if self.is_authenticated():
            return st.session_state.user
        return None
    
    def logout(self):
        """Logout current user and clear ALL session data"""
        # Clear user data
        if 'user' in st.session_state:
            del st.session_state.user
        
        # Clear ALL quiz-related data
        quiz_keys_to_clear = [
            'quiz_manager',
            'quiz_generated', 
            'quiz_submitted',
            'current_topic',
            'current_sub_topic', 
            'current_difficulty',
            'viewing_quiz_id',
            'view_mode',
            'show_history',
            'retake_topic',
            'retake_difficulty', 
            'retake_type',
            'retake_questions',
            'rerun_trigger'
        ]
        
        for key in quiz_keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        st.rerun()

