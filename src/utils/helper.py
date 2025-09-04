import os
import streamlit as st
import pandas as pd
from typing import Dict
from src.generator.question_generator import QuestionGenerator
from src.models.simple_session import SimpleSessionManager
import urllib.parse
import time

def rerun():
    st.session_state['rerun_trigger'] = not st.session_state.get('rerun_trigger', False)

class QuizManager:
    def __init__(self):
        self.questions = []
        self.user_answers = []
        self.results = []
        self.current_session_id = None
        self.question_start_times = []
        
        # Initialize question logger and recommendation engine safely
        try:
            from src.models.question_log import QuestionLogger, SmartRecommendationEngine
            self.question_logger = QuestionLogger()
            self.recommendation_engine = SmartRecommendationEngine(self.question_logger)
            self.has_ai_features = True
        except ImportError:
            print("AI features not available - question_log module not found")
            self.question_logger = None
            self.recommendation_engine = None
            self.has_ai_features = False
    
    def generate_questions(self, generator: QuestionGenerator, topic: str, 
                         question_type: str, difficulty: str, num_questions: int):
        self.questions = []
        self.user_answers = []
        self.results = []
        self.question_start_times = []
        self.current_session_id = None

        try:
            for i in range(num_questions):
                if question_type == "Multiple Choice":
                    question = generator.generate_mcq(topic, difficulty.lower())
                    
                    self.questions.append({
                        'type': 'MCQ',
                        'question': question.question,
                        'options': question.options,
                        'correct_answer': question.correct_answer,
                        'explanation': getattr(question, 'explanation', 'No explanation available')
                    })
                else:
                    question = generator.generate_fill_blank(topic, difficulty.lower())
                    
                    self.questions.append({
                        'type': 'Fill in the blank',
                        'question': question.question,
                        'correct_answer': question.answer,
                        'explanation': getattr(question, 'explanation', 'No explanation available')
                    })
                    
        except Exception as e:
            st.error(f"Error generating question {e}")
            return False
        
        return True

    def attempt_quiz(self):
        for i, q in enumerate(self.questions):
            st.markdown(f"**Question {i+1}: {q['question']}**")
            
            # Record start time for this question
            if len(self.question_start_times) <= i:
                self.question_start_times.append(time.time())

            if q['type'] == 'MCQ':
                user_answer = st.radio(
                    f"Select an answer for Question {i+1}",
                    q['options'],
                    key=f"mcq_{i}"
                )
            else:
                user_answer = st.text_input(
                    f"Fill in the blank for Question {i+1}",
                    key=f"fill_blank_{i}"
                )

            if len(self.user_answers) <= i:
                self.user_answers.append(user_answer)
            else:
                self.user_answers[i] = user_answer

    def evaluate_quiz(self):
        self.results = []

        for i, (q, user_ans) in enumerate(zip(self.questions, self.user_answers)):
            # Calculate time taken for this question
            time_taken = int(time.time() - self.question_start_times[i]) if i < len(self.question_start_times) else 0
            
            result_dict = {
                'question_number': i+1,
                'question': q['question'],
                'question_type': q["type"],
                'user_answer': user_ans,
                'correct_answer': q["correct_answer"],
                'explanation': q.get('explanation', ''),
                'time_taken': time_taken,
                "is_correct": False
            }

            if q['type'] == 'MCQ':
                result_dict['options'] = q['options']
                result_dict["is_correct"] = user_ans == q["correct_answer"]
            else:
                result_dict['options'] = []
                result_dict["is_correct"] = user_ans.strip().lower() == q['correct_answer'].strip().lower()

            self.results.append(result_dict)

        # Save session and log questions if user is logged in
        if 'user' in st.session_state and st.session_state.user and self.results:
            session_manager = SimpleSessionManager()
            
            correct_count = sum(1 for result in self.results if result["is_correct"])
            score_percentage = (correct_count / len(self.results)) * 100
            
            # Save quiz session
            quiz_data = {
                'topic': st.session_state.get('current_topic', ''),
                'sub_topic': st.session_state.get('current_sub_topic', ''),
                'question_type': self.questions[0]['type'] if self.questions else '',
                'difficulty': st.session_state.get('current_difficulty', ''),
                'num_questions': len(self.questions),
                'score': score_percentage,
                'questions_data': self.questions,
                'user_answers': self.user_answers,
                'results_data': self.results
            }
            
            self.current_session_id = session_manager.save_quiz_session(
                st.session_state.user['id'], quiz_data
            )
            
            # Log each question individually for AI analysis (if available)
            if self.has_ai_features:
                self._log_individual_questions()
    
    def _log_individual_questions(self):
        """Log each question with user performance for AI analysis"""
        if not self.has_ai_features or not self.current_session_id or not self.results:
            return
        
        user_id = st.session_state.user['id']
        main_topic = st.session_state.get('current_topic', '')
        sub_topic = st.session_state.get('current_sub_topic', '')
        difficulty = st.session_state.get('current_difficulty', '')
        
        for i, (question, result) in enumerate(zip(self.questions, self.results)):
            question_data = {
                'topic': main_topic,
                'sub_topic': sub_topic,
                'difficulty': difficulty,
                'question_type': question['type'],
                'question_text': question['question'],
                'options': question.get('options', []),
                'correct_answer': question['correct_answer'],
                'user_answer': result['user_answer'],
                'is_correct': result['is_correct'],
                'time_taken': result.get('time_taken', 0),
                'explanation': question.get('explanation', '')
            }
            
            try:
                self.question_logger.log_question(user_id, self.current_session_id, question_data)
            except Exception as e:
                print(f"Error logging question: {e}")
    
    def get_smart_recommendations(self, user_id: int) -> Dict:
        """Get AI-powered quiz recommendations based on user history"""
        if not self.has_ai_features or not self.recommendation_engine:
            # Return empty recommendations if AI features not available
            return {
                'has_recommendations': False,
                'weak_topics': [],
                'suggested_quiz': None,
                'focus_areas': [],
                'motivation_message': "Keep practicing to unlock AI recommendations!"
            }
        
        try:
            return self.recommendation_engine.get_personalized_recommendations(user_id)
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return {
                'has_recommendations': False,
                'weak_topics': [],
                'suggested_quiz': None,
                'focus_areas': [],
                'motivation_message': "AI recommendations temporarily unavailable."
            }

    def generate_result_dataframe(self):
        """Generate pandas DataFrame from quiz results"""
        if not self.results:
            return pd.DataFrame()
        return pd.DataFrame(self.results)

    def save_to_csv(self, filename_prefix="quiz_results"):
        """Save quiz results to CSV file"""
        if not self.results:
            st.warning("No results to save !!")
            return None
        
        df = self.generate_result_dataframe()

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{filename_prefix}_{timestamp}.csv"

        os.makedirs('results', exist_ok=True)
        full_path = os.path.join('results', unique_filename)

        try:
            df.to_csv(full_path, index=False)
            st.success("Results saved successfully....")
            return full_path
        
        except Exception as e:
            st.error(f"Failed to save results {e}")
            return None

    def generate_ai_links(self, question: str, correct_answer: str, topic: str, user_answer: str = ""):
        """Generate AI assistance links"""
        if user_answer and user_answer != correct_answer:
            query = f"Explain why '{correct_answer}' is the correct answer to this {topic} question: '{question}'. Also explain why '{user_answer}' is wrong."
        else:
            query = f"Explain this {topic} concept in detail: '{question}' Answer: '{correct_answer}'"
        
        encoded_query = urllib.parse.quote(query)
        
        return {
            'chatgpt': f"https://chat.openai.com/?q={encoded_query}",
            'gemini': f"https://gemini.google.com/?q={encoded_query}",
            'claude': f"https://claude.ai/?q={encoded_query}",
            'perplexity': f"https://www.perplexity.ai/?q={encoded_query}"
        }
