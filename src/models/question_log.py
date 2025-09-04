import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class QuestionLogger:
    def __init__(self, db_path: str = "studyai.db"):
        self.db_path = db_path
        self.init_tables()
    
    def init_tables(self):
        """Initialize question logging table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                session_id INTEGER,
                topic TEXT NOT NULL,
                sub_topic TEXT,
                difficulty TEXT,
                question_type TEXT,
                question_text TEXT,
                options TEXT, -- JSON for MCQ options
                correct_answer TEXT,
                user_answer TEXT,
                is_correct BOOLEAN,
                time_taken INTEGER, -- seconds
                explanation TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (session_id) REFERENCES quiz_sessions (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_question(self, user_id: int, session_id: int, question_data: Dict):
        """Log individual question with user performance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO question_log (
                    user_id, session_id, topic, sub_topic, difficulty, question_type,
                    question_text, options, correct_answer, user_answer, is_correct,
                    time_taken, explanation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                int(user_id),
                int(session_id),
                question_data.get('topic', ''),
                question_data.get('sub_topic', ''),
                question_data.get('difficulty', ''),
                question_data.get('question_type', ''),
                question_data.get('question_text', ''),
                json.dumps(question_data.get('options', [])),
                question_data.get('correct_answer', ''),
                question_data.get('user_answer', ''),
                bool(question_data.get('is_correct', False)),
                int(question_data.get('time_taken', 0)),
                question_data.get('explanation', '')
            ])
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Question logging error: {e}")
            return False
    
    def get_recent_questions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's recent questions for analysis"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM question_log 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', [int(user_id), int(limit)])
            
            questions = []
            for row in cursor.fetchall():
                questions.append({
                    'id': row['id'],
                    'topic': row['topic'],
                    'sub_topic': row['sub_topic'],
                    'difficulty': row['difficulty'],
                    'question_type': row['question_type'],
                    'question_text': row['question_text'],
                    'is_correct': bool(row['is_correct']),
                    'created_at': row['created_at']
                })
            
            conn.close()
            return questions
            
        except Exception as e:
            print(f"Get recent questions error: {e}")
            return []
    
    def analyze_weak_topics(self, user_id: int, days: int = 7) -> Dict[str, Dict]:
        """Analyze user's weak topics from recent performance"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get questions from last N days
            cursor.execute('''
                SELECT topic, sub_topic, difficulty, is_correct, COUNT(*) as question_count
                FROM question_log 
                WHERE user_id = ? AND created_at >= datetime('now', '-{} days')
                GROUP BY topic, sub_topic, difficulty, is_correct
                ORDER BY topic, sub_topic
            '''.format(days), [int(user_id)])
            
            # Analyze performance by topic
            topic_analysis = {}
            for row in cursor.fetchall():
                topic_key = row['topic']
                if row['sub_topic']:
                    topic_key = f"{row['topic']} - {row['sub_topic']}"
                
                if topic_key not in topic_analysis:
                    topic_analysis[topic_key] = {
                        'total_questions': 0,
                        'correct_answers': 0,
                        'wrong_answers': 0,
                        'accuracy': 0.0,
                        'difficulty_breakdown': {},
                        'needs_practice': False
                    }
                
                # Update counts
                topic_analysis[topic_key]['total_questions'] += row['question_count']
                if row['is_correct']:
                    topic_analysis[topic_key]['correct_answers'] += row['question_count']
                else:
                    topic_analysis[topic_key]['wrong_answers'] += row['question_count']
                
                # Track difficulty breakdown
                diff = row['difficulty']
                if diff not in topic_analysis[topic_key]['difficulty_breakdown']:
                    topic_analysis[topic_key]['difficulty_breakdown'][diff] = {'correct': 0, 'total': 0}
                
                topic_analysis[topic_key]['difficulty_breakdown'][diff]['total'] += row['question_count']
                if row['is_correct']:
                    topic_analysis[topic_key]['difficulty_breakdown'][diff]['correct'] += row['question_count']
            
            # Calculate accuracy and identify weak topics
            weak_topics = {}
            for topic, data in topic_analysis.items():
                if data['total_questions'] > 0:
                    data['accuracy'] = (data['correct_answers'] / data['total_questions']) * 100
                    
                    # Mark as weak if accuracy < 70% and at least 2 questions attempted
                    if data['accuracy'] < 70 and data['total_questions'] >= 2:
                        data['needs_practice'] = True
                        weak_topics[topic] = data
            
            conn.close()
            return {
                'all_topics': topic_analysis,
                'weak_topics': weak_topics,
                'analysis_period_days': days
            }
            
        except Exception as e:
            print(f"Weak topic analysis error: {e}")
            return {'all_topics': {}, 'weak_topics': {}, 'analysis_period_days': days}

class SmartRecommendationEngine:
    def __init__(self, question_logger: QuestionLogger):
        self.logger = question_logger
    
    def get_personalized_recommendations(self, user_id: int) -> Dict:
        """Generate personalized quiz recommendations based on user performance"""
        analysis = self.logger.analyze_weak_topics(user_id, days=14)
        weak_topics = analysis['weak_topics']
        
        recommendations = {
            'has_recommendations': len(weak_topics) > 0,
            'weak_topics': list(weak_topics.keys()),
            'suggested_quiz': None,
            'focus_areas': [],
            'motivation_message': ""
        }
        
        if weak_topics:
            # Find the weakest topic
            weakest_topic = min(weak_topics.items(), key=lambda x: x[1]['accuracy'])
            topic_name, topic_data = weakest_topic
            
            # Extract main topic and sub-topic
            if ' - ' in topic_name:
                main_topic, sub_topic = topic_name.split(' - ', 1)
            else:
                main_topic, sub_topic = topic_name, ""
            
            # Determine recommended difficulty
            difficulty_breakdown = topic_data['difficulty_breakdown']
            recommended_difficulty = "Easy"  # Start with easier questions for weak topics
            
            for diff in ['Easy', 'Medium', 'Hard']:
                if diff in difficulty_breakdown:
                    if difficulty_breakdown[diff]['correct'] / difficulty_breakdown[diff]['total'] < 0.5:
                        recommended_difficulty = diff
                        break
            
            recommendations['suggested_quiz'] = {
                'main_topic': main_topic,
                'sub_topic': sub_topic,
                'difficulty': recommended_difficulty,
                'question_type': 'Multiple Choice',  # Default
                'num_questions': min(5, max(3, topic_data['wrong_answers'])),
                'reason': f"You have {topic_data['accuracy']:.0f}% accuracy in this topic"
            }
            
            recommendations['focus_areas'] = [
                f"{topic}: {data['accuracy']:.0f}% accuracy" 
                for topic, data in list(weak_topics.items())[:3]
            ]
            
            recommendations['motivation_message'] = self._generate_motivation_message(topic_data['accuracy'])
        else:
            recommendations['motivation_message'] = "Great job! You're performing well across all topics. Try exploring new areas or increasing difficulty!"
        
        return recommendations
    
    def _generate_motivation_message(self, accuracy: float) -> str:
        """Generate motivational message based on accuracy"""
        if accuracy < 40:
            return "🎯 Focus time! Let's strengthen your foundation with some targeted practice."
        elif accuracy < 60:
            return "📈 You're improving! A few more practice sessions will boost your confidence."
        elif accuracy < 80:
            return "💪 Almost there! Fine-tune your knowledge with focused practice."
        else:
            return "🌟 Excellent progress! Ready to tackle more challenging questions?"
