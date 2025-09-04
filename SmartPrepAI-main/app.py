import os
import streamlit as st
from dotenv import load_dotenv
from src.utils.helper import *
from src.generator.question_generator import QuestionGenerator
from src.models.auth import AuthManager
from src.models.simple_session import SimpleSessionManager
from src.components.quiz_history_sidebar import show_quiz_history_right_sidebar, render_history_content, show_revision_view

load_dotenv()

def show_login_signup():
    """Show login/signup interface"""
    auth = AuthManager()
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.header("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login")
            
            if login_btn and username and password:
                user = auth.login_user(username, password)
                if user:
                    st.session_state.user = user
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    with tab2:
        st.header("Sign Up")
        with st.form("signup_form"):
            new_username = st.text_input("Choose Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            signup_btn = st.form_submit_button("Sign Up")
            
            if signup_btn and new_username and new_email and new_password:
                if new_password != confirm_password:
                    st.error("Passwords don't match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    if auth.register_user(new_username, new_email, new_password):
                        st.success("Account created successfully! Please login.")
                    else:
                        st.error("Username or email already exists")

def check_auto_suggestions():
    """Check if user needs automatic suggestions based on recent poor performance"""
    if 'user' not in st.session_state or not st.session_state.user:
        return None
    
    try:
        quiz_manager = st.session_state.quiz_manager
        if not hasattr(quiz_manager, 'question_logger') or not quiz_manager.question_logger:
            return None
        
        user_id = st.session_state.user['id']
        
        # Get last 10 questions from recent sessions
        recent_questions = quiz_manager.question_logger.get_recent_questions(user_id, 10)
        
        if len(recent_questions) >= 5:  # Need at least 5 questions to analyze
            # Group by topic + subtopic
            topic_performance = {}
            
            for q in recent_questions:
                topic_key = q['topic']
                if q.get('sub_topic'):
                    topic_key = f"{q['topic']} - {q['sub_topic']}"
                
                if topic_key not in topic_performance:
                    topic_performance[topic_key] = {'correct': 0, 'total': 0}
                
                topic_performance[topic_key]['total'] += 1
                if q['is_correct']:
                    topic_performance[topic_key]['correct'] += 1
            
            # Check for topics with < 50% accuracy and at least 3 attempts
            weak_topics = []
            for topic, perf in topic_performance.items():
                if perf['total'] >= 3:  # At least 3 attempts
                    accuracy = (perf['correct'] / perf['total']) * 100
                    if accuracy < 50:
                        weak_topics.append({
                            'topic': topic,
                            'accuracy': accuracy,
                            'attempts': perf['total']
                        })
            
            if weak_topics:
                return weak_topics[0]  # Return the weakest topic
    
    except Exception as e:
        print(f"Auto suggestion check error: {e}")
    
    return None

def show_auto_suggestion_popup(weak_topic_info):
    """Show automatic suggestion popup when user is struggling"""
    topic = weak_topic_info['topic']
    accuracy = weak_topic_info['accuracy']
    attempts = weak_topic_info['attempts']
    
    # Create a modal-like warning
    st.error("🎯 **Performance Alert!**")
    
    with st.container():
        st.write(f"**Struggling with {topic}?**")
        st.write(f"Your recent accuracy: **{accuracy:.0f}%** in {attempts} attempts")
        st.write("💡 **Our AI recommends taking a focused practice quiz to improve!**")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("🚀 Yes, Help Me!", type="primary", use_container_width=True):
                return "ACCEPT_AUTO_SUGGESTION", weak_topic_info
        
        with col2:
            if st.button("⏭️ Skip for Now", use_container_width=True):
                return "SKIP_AUTO_SUGGESTION", None
                
        with col3:
            if st.button("🔕 Don't Ask Again", use_container_width=True):
                # Set a flag to not show auto suggestions for this session
                st.session_state.disable_auto_suggestions = True
                return "DISABLE_AUTO_SUGGESTION", None
    
    return None, None

def generate_quiz_from_suggestion(suggestion_data):
    """Generate quiz directly from AI suggestion"""
    try:
        # Parse topic and subtopic
        topic_full = suggestion_data['main_topic']
        if suggestion_data.get('sub_topic'):
            topic_full = f"{suggestion_data['main_topic']} - {suggestion_data['sub_topic']}"
        
        # Set session state for tracking
        st.session_state.current_topic = suggestion_data['main_topic']
        st.session_state.current_sub_topic = suggestion_data.get('sub_topic', '')
        st.session_state.current_difficulty = suggestion_data['difficulty']
        
        # Clear previous states
        st.session_state.quiz_generated = False
        st.session_state.quiz_submitted = False
        
        # Generate quiz directly
        with st.spinner("🤖 Generating personalized quiz based on your weak areas..."):
            generator = QuestionGenerator()
            success = st.session_state.quiz_manager.generate_questions(
                generator, 
                topic_full,
                suggestion_data.get('question_type', 'Multiple Choice'),
                suggestion_data['difficulty'],
                suggestion_data['num_questions']
            )
        
        if success:
            st.session_state.quiz_generated = True
            st.success("✅ AI-powered quiz generated! Let's improve your weak areas!")
        else:
            st.error("❌ Failed to generate quiz. Please try again.")
        
        return success
        
    except Exception as e:
        st.error(f"❌ Quiz generation error: {e}")
        return False

def show_smart_recommendations():
    """Display AI-powered quiz recommendations with direct generation"""
    if 'user' not in st.session_state or not st.session_state.user:
        return None, None, None, None, None
    
    # Only show recommendations when ready for a new quiz
    if st.session_state.get('quiz_generated', False) and not st.session_state.get('quiz_submitted', False):
        return None, None, None, None, None
    
    try:
        quiz_manager = st.session_state.quiz_manager
        if hasattr(quiz_manager, 'get_smart_recommendations'):
            recommendations = quiz_manager.get_smart_recommendations(st.session_state.user['id'])
        else:
            recommendations = {'has_recommendations': False, 'motivation_message': "Take more quizzes to unlock AI recommendations!"}
        
        if recommendations['has_recommendations']:
            with st.expander("🤖 AI-Powered Quiz Recommendations", expanded=True):
                st.info(recommendations['motivation_message'])
                
                suggested = recommendations.get('suggested_quiz')
                if suggested:
                    st.write("**🎯 Recommended Quiz for You:**")
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Topic:** {suggested['main_topic']}")
                        if suggested.get('sub_topic'):
                            st.write(f"**Sub-topic:** {suggested['sub_topic']}")
                        st.write(f"**Difficulty:** {suggested['difficulty']}")
                        st.write(f"**Questions:** {suggested['num_questions']}")
                        st.caption(f"💡 {suggested['reason']}")
                    
                    with col2:
                        if st.button("🚀 Generate AI Quiz", type="primary"):
                            # DIRECT QUIZ GENERATION - No parameter setting
                            return "GENERATE_DIRECT", suggested
                
                if recommendations.get('focus_areas'):
                    st.write("**📊 Your Performance Analysis:**")
                    for area in recommendations['focus_areas']:
                        st.write(f"• {area}")
        else:
            st.success("🌟 " + recommendations.get('motivation_message', 'Keep practicing!'))
    
    except Exception as e:
        print(f"Smart recommendations error: {e}")
        st.info("🤖 AI recommendations will appear after you take more quizzes!")
    
    return None, None, None, None, None

def show_dashboard():
    """Show user dashboard with simple analytics"""
    user = st.session_state.user
    
    session_manager = SimpleSessionManager()
    
    st.header(f"Welcome back, {user['username']}! 👋")
    
    user_sessions = session_manager.get_user_sessions(user['id'], 100)
    
    total_quizzes = len(user_sessions)
    avg_score = sum([s['score'] for s in user_sessions]) / len(user_sessions) if user_sessions else 0
    max_score = max([s['score'] for s in user_sessions]) if user_sessions else 0
    
    from datetime import datetime, timedelta
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_sessions = [s for s in user_sessions if s['created_at'] >= seven_days_ago.strftime('%Y-%m-%d')]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Quizzes", total_quizzes)
    with col2:
        st.metric("Average Score", f"{avg_score:.1f}%")
    with col3:
        st.metric("Best Score", f"{max_score:.1f}%")
    with col4:
        st.metric("Quizzes This Week", len(recent_sessions))
    
    # Show AI-powered performance insights with error handling
    if total_quizzes > 0:
        st.subheader("🤖 AI Performance Insights")
        try:
            quiz_manager = st.session_state.quiz_manager
            if hasattr(quiz_manager, 'question_logger') and quiz_manager.question_logger:
                analysis = quiz_manager.question_logger.analyze_weak_topics(user['id'], days=14)
                
                if analysis['weak_topics']:
                    st.warning("**Areas for Improvement:**")
                    for topic, data in list(analysis['weak_topics'].items())[:3]:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"• **{topic}**: {data['accuracy']:.0f}% accuracy")
                        with col2:
                            st.write(f"({data['total_questions']} questions)")
                else:
                    st.success("🎉 **Great job!** You're performing well across all topics!")
            else:
                st.info("📊 AI insights will appear after you take more quizzes!")
        except Exception as e:
            print(f"Dashboard AI insights error: {e}")
            st.info("📊 AI insights will appear after you take more quizzes!")
    
    st.subheader("Recent Quiz Sessions")
    recent_sessions_display = session_manager.get_user_sessions(user['id'], 5)
    
    if recent_sessions_display:
        for session in recent_sessions_display:
            with st.expander(f"{session['display_title']} - {session['score']:.1f}% ({session['short_date']})"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Type:** {session['question_type']}")
                    st.write(f"**Difficulty:** {session['difficulty']}")
                with col2:
                    st.write(f"**Questions:** {session['num_questions']}")
                    st.write(f"**Score:** {session['score']:.1f}%")
                with col3:
                    if st.button(f"📖 Review Quiz", key=f"review_{session['id']}"):
                        st.session_state.viewing_quiz_id = session['id']
                        st.session_state.view_mode = 'revision'
                        st.rerun()
                    if st.button(f"🔄 Retake Similar", key=f"retake_{session['id']}"):
                        st.session_state.retake_topic = session['topic']
                        st.session_state.retake_difficulty = session['difficulty']
                        st.session_state.retake_type = session['question_type']
                        st.session_state.retake_questions = session['num_questions']
                        st.info("Quiz settings loaded! Switch to 'New Quiz' tab.")
    else:
        st.info("No previous sessions found. Start your first quiz!")
    
    if len(user_sessions) > 1:
        st.subheader("Performance by Topic")
        
        topic_stats = {}
        for session in user_sessions:
            topic = session['topic']
            if topic not in topic_stats:
                topic_stats[topic] = {'scores': [], 'count': 0}
            topic_stats[topic]['scores'].append(session['score'])
            topic_stats[topic]['count'] += 1
        
        for topic, stats in topic_stats.items():
            avg_topic_score = sum(stats['scores']) / len(stats['scores'])
            
            # Color code based on performance
            if avg_topic_score >= 80:
                st.success(f"**{topic}**: {stats['count']} quizzes, {avg_topic_score:.1f}% average ✨")
            elif avg_topic_score >= 60:
                st.info(f"**{topic}**: {stats['count']} quizzes, {avg_topic_score:.1f}% average 📈")
            else:
                st.warning(f"**{topic}**: {stats['count']} quizzes, {avg_topic_score:.1f}% average 🎯")

def clear_quiz_states():
    """Clear all quiz-related states for fresh start"""
    st.session_state.quiz_generated = False
    st.session_state.quiz_submitted = False
    if hasattr(st.session_state.quiz_manager, 'questions'):
        st.session_state.quiz_manager.questions = []
        st.session_state.quiz_manager.user_answers = []
        st.session_state.quiz_manager.results = []

def main():
    st.set_page_config(page_title="StudyBuddyAI", layout="wide")
    
    auth = AuthManager()
    
    # Initialize session states ONLY if user is authenticated
    if not auth.is_authenticated():
        st.title("StudyBuddyAI - Login Required")
        show_login_signup()
        return
    
    # User is authenticated - initialize session states
    if 'quiz_manager' not in st.session_state:
        st.session_state.quiz_manager = QuizManager()
    
    if 'quiz_generated' not in st.session_state:
        st.session_state.quiz_generated = False
    
    if 'quiz_submitted' not in st.session_state:
        st.session_state.quiz_submitted = False
    
    if 'rerun_trigger' not in st.session_state:
        st.session_state.rerun_trigger = False
    
    # Check if user is viewing a quiz for revision
    if st.session_state.get('view_mode') == 'revision' and st.session_state.get('viewing_quiz_id'):
        
        # Create layout with right sidebar for revision mode
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.title("StudyBuddyAI - Quiz Revision")
            show_revision_view(st.session_state.viewing_quiz_id)
        
        with col2:
            render_history_content()
        
        return
    
    # Normal app flow with right sidebar toggle
    # Header with history toggle
    col1, col2 = st.columns([6, 1])
    
    with col1:
        st.title("StudyBuddyAI")
    
    with col2:
        if st.button("📚 History", help="Toggle quiz history"):
            st.session_state.show_history = not st.session_state.get('show_history', False)
            st.rerun()
    
    # Left sidebar for logout only
    with st.sidebar:
        if st.button("Logout"):
            auth.logout()
    
    # Main layout with optional right sidebar
    if st.session_state.get('show_history', False):
        main_col, history_col = st.columns([3, 1])
    else:
        main_col = st.container()
        history_col = None
    
    # Main content area
    with main_col:
        tab1, tab2 = st.tabs(["New Quiz", "Dashboard"])
        
        with tab1:
            # Check for auto-suggestions first (if not disabled)
            auto_suggestion_result = None, None
            if not st.session_state.get('disable_auto_suggestions', False):
                weak_topic = check_auto_suggestions()
                if weak_topic and not st.session_state.get('quiz_generated', False) and not st.session_state.get('quiz_submitted', False):
                    auto_suggestion_result = show_auto_suggestion_popup(weak_topic)
            
            # Handle auto-suggestion responses
            if auto_suggestion_result[0] == "ACCEPT_AUTO_SUGGESTION":
                # Generate quiz directly from weak topic
                weak_info = auto_suggestion_result[1]
                topic_parts = weak_info['topic'].split(' - ', 1)
                main_topic = topic_parts[0]
                sub_topic = topic_parts[1] if len(topic_parts) > 1 else ""
                
                suggestion_data = {
                    'main_topic': main_topic,
                    'sub_topic': sub_topic,
                    'difficulty': 'Easy',  # Start with easy for struggling topics
                    'question_type': 'Multiple Choice',
                    'num_questions': 5,
                    'reason': f'Auto-suggested due to {weak_info["accuracy"]:.0f}% accuracy'
                }
                
                generate_quiz_from_suggestion(suggestion_data)
                st.rerun()
                
            elif auto_suggestion_result[0] in ["SKIP_AUTO_SUGGESTION", "DISABLE_AUTO_SUGGESTION"]:
                st.rerun()
            
            # Show AI recommendations (if no auto-suggestion is active)
            if not weak_topic or st.session_state.get('disable_auto_suggestions', False):
                if not st.session_state.get('quiz_generated', False) or st.session_state.get('quiz_submitted', False):
                    ai_result = show_smart_recommendations()
                    
                    # Handle direct AI quiz generation
                    if ai_result and ai_result[0] == "GENERATE_DIRECT":
                        generate_quiz_from_suggestion(ai_result[1])
                        st.rerun()
            
            # Quiz settings in left sidebar
            with st.sidebar:
                st.header("Quiz Settings")
                
                default_topic_index = 0
                default_difficulty_index = 1
                default_type_index = 0
                default_questions = 5
                
                # Check for retake settings
                if 'retake_topic' in st.session_state:
                    topics = ["Operating Systems", "Computer Networks", "DBMS", "DSA", "OOPs", 
                             "Machine Learning", "Software Engineering", "C++", "Java", "Javascript", "Python"]
                    if st.session_state.retake_topic in topics:
                        default_topic_index = topics.index(st.session_state.retake_topic)
                    
                    difficulties = ["Easy", "Medium", "Hard"]
                    if st.session_state.retake_difficulty in difficulties:
                        default_difficulty_index = difficulties.index(st.session_state.retake_difficulty)
                    
                    question_types = ["Multiple Choice", "Fill in the Blank"]
                    if st.session_state.retake_type in question_types:
                        default_type_index = question_types.index(st.session_state.retake_type)
                    
                    default_questions = st.session_state.retake_questions
                    
                    st.info("🔄 Retake settings loaded")
                    
                    del st.session_state.retake_topic
                    del st.session_state.retake_difficulty
                    del st.session_state.retake_type
                    del st.session_state.retake_questions
                
                question_type = st.selectbox(
                    "Select Question Type",
                    ["Multiple Choice", "Fill in the Blank"],
                    index=default_type_index
                )
                
                main_topic = st.selectbox(
                    "Select Main Topic",
                    ["Operating Systems", "Computer Networks", "DBMS", "DSA", "OOPs", 
                     "Machine Learning", "Software Engineering", "C++", "Java", "Javascript", "Python"],
                    index=default_topic_index
                )
                
                sub_topic = st.text_input(
                    "Enter Sub-topic",
                    placeholder="e.g., Paging, TCP/IP, Normalization"
                )
                
                if sub_topic:
                    topic = f"{main_topic} - {sub_topic}"
                    st.session_state.current_sub_topic = sub_topic
                else:
                    topic = main_topic
                    st.session_state.current_sub_topic = ""
                    
                st.session_state.current_topic = main_topic
                
                difficulty = st.selectbox(
                    "Difficulty Level",
                    ["Easy", "Medium", "Hard"],
                    index=default_difficulty_index
                )
                st.session_state.current_difficulty = difficulty
                
                num_questions = st.number_input(
                    "Number of Questions",
                    min_value=1, max_value=10, value=default_questions
                )
                
                if st.button("Generate Quiz", type="primary"):
                    # Clear previous states before generating new quiz
                    clear_quiz_states()
                    
                    with st.spinner("🤖 AI is generating personalized questions..."):
                        try:
                            generator = QuestionGenerator()
                            success = st.session_state.quiz_manager.generate_questions(
                                generator, topic, question_type, difficulty, num_questions
                            )
                        except Exception as e:
                            st.error(f"❌ Question generation failed: {e}")
                            st.info("💡 Tip: Check your internet connection and API settings")
                            success = False
                    
                    st.session_state.quiz_generated = success
                    if success:
                        st.success("✅ Quiz generated successfully!")
                    st.rerun()
            
            # Show quiz content ONLY if quiz is generated and not submitted
            if st.session_state.quiz_generated and not st.session_state.quiz_submitted:
                if st.session_state.quiz_manager.questions:
                    st.header("📝 Quiz Time!")
                    
                    # Show if it's an AI-generated quiz
                    if hasattr(st.session_state, 'current_topic'):
                        topic_display = st.session_state.current_topic
                        if st.session_state.get('current_sub_topic'):
                            topic_display += f" - {st.session_state.current_sub_topic}"
                        st.write(f"**🤖 Topic:** {topic_display} | **Difficulty:** {st.session_state.get('current_difficulty', 'Medium')} | **Questions:** {len(st.session_state.quiz_manager.questions)}")
                    
                    st.session_state.quiz_manager.attempt_quiz()
                    
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.button("🎯 Submit Quiz", type="primary", use_container_width=True):
                            with st.spinner("🔍 Evaluating your answers..."):
                                st.session_state.quiz_manager.evaluate_quiz()
                                st.session_state.quiz_submitted = True
                            st.rerun()
            
            # Show results and quick continue option
            elif st.session_state.quiz_submitted:
                st.header("📊 Quiz Results")
                results_df = st.session_state.quiz_manager.generate_result_dataframe()
                
                if not results_df.empty:
                    correct_count = results_df["is_correct"].sum()
                    total_questions = len(results_df)
                    score_percentage = (correct_count/total_questions)*100
                    
                    # Quick action buttons at the top for continuous practice
                    st.subheader("🚀 Quick Actions")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button("🔄 Same Topic Again", use_container_width=True):
                            # Keep same settings, generate new quiz
                            current_topic = st.session_state.get('current_topic', 'DSA')
                            current_sub_topic = st.session_state.get('current_sub_topic', '')
                            topic_full = f"{current_topic} - {current_sub_topic}" if current_sub_topic else current_topic
                            
                            clear_quiz_states()
                            
                            with st.spinner("🔄 Generating another quiz on the same topic..."):
                                generator = QuestionGenerator()
                                success = st.session_state.quiz_manager.generate_questions(
                                    generator, topic_full, "Multiple Choice", 
                                    st.session_state.get('current_difficulty', 'Medium'), 5
                                )
                                if success:
                                    st.session_state.quiz_generated = True
                            st.rerun()
                    
                    with col2:
                        if st.button("⬆️ Increase Difficulty", use_container_width=True):
                            # Increase difficulty and generate
                            current_diff = st.session_state.get('current_difficulty', 'Easy')
                            next_diff = {'Easy': 'Medium', 'Medium': 'Hard', 'Hard': 'Hard'}[current_diff]
                            st.session_state.current_difficulty = next_diff
                            
                            current_topic = st.session_state.get('current_topic', 'DSA')
                            current_sub_topic = st.session_state.get('current_sub_topic', '')
                            topic_full = f"{current_topic} - {current_sub_topic}" if current_sub_topic else current_topic
                            
                            clear_quiz_states()
                            
                            with st.spinner(f"⬆️ Generating {next_diff} difficulty quiz..."):
                                generator = QuestionGenerator()
                                success = st.session_state.quiz_manager.generate_questions(
                                    generator, topic_full, "Multiple Choice", next_diff, 5
                                )
                                if success:
                                    st.session_state.quiz_generated = True
                            st.rerun()
                    
                    with col3:
                        if st.button("🤖 AI Suggestion", use_container_width=True):
                            # Clear states and show AI recommendation
                            clear_quiz_states()
                            st.rerun()
                    
                    with col4:
                        if st.button("📊 View Progress", use_container_width=True):
                            st.info("👆 Switch to Dashboard tab to see detailed progress!")
                    
                    # Enhanced score display
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Score", f"{score_percentage:.1f}%")
                    with col2:
                        st.metric("Correct", f"{correct_count}/{total_questions}")
                    with col3:
                        improvement = "📈" if score_percentage >= 60 else "🎯"
                        st.metric("Status", f"{improvement} Keep going!")
                    
                    # Show score message
                    if score_percentage >= 80:
                        st.success(f"🎉 Excellent! Score: {score_percentage:.1f}% - You're mastering this topic!")
                    elif score_percentage >= 60:
                        st.info(f"👍 Good job! Score: {score_percentage:.1f}% - Keep up the great work!")
                    else:
                        st.warning(f"📚 Score: {score_percentage:.1f}% - Perfect opportunity to learn and improve!")
                    
                    st.subheader("🔍 Detailed Results with AI Explanations")
                    for _, result in results_df.iterrows():
                        question_num = result['question_number']
                        
                        if result['is_correct']:
                            st.success(f"✅ **Question {question_num}**: {result['question']}")
                        else:
                            st.error(f"❌ **Question {question_num}**: {result['question']}")
                            st.write(f"**Your answer:** {result['user_answer']}")
                            st.write(f"**Correct answer:** {result['correct_answer']}")
                        
                        if result.get('explanation'):
                            st.info(f"💡 **AI Explanation:** {result['explanation']}")
                        
                        topic_name = st.session_state.get('current_topic', 'General')
                        ai_links = st.session_state.quiz_manager.generate_ai_links(
                            result['question'], 
                            result['correct_answer'], 
                            topic_name, 
                            result['user_answer']
                        )
                        
                        st.write("**🤖 Need deeper understanding? Ask AI assistants:**")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.markdown(f"[💬 ChatGPT]({ai_links['chatgpt']})")
                        with col2:
                            st.markdown(f"[✨ Gemini]({ai_links['gemini']})")
                        with col3:
                            st.markdown(f"[🧠 Claude]({ai_links['claude']})")
                        with col4:
                            st.markdown(f"[🔍 Perplexity]({ai_links['perplexity']})")
                        
                        st.markdown("---")
                    
                    # Show updated AI recommendations after quiz
                    st.markdown("---")
                    try:
                        new_recommendations = st.session_state.quiz_manager.get_smart_recommendations(st.session_state.user['id'])
                        if new_recommendations['has_recommendations']:
                            st.info("🤖 **Updated AI Recommendations:**")
                            st.write(new_recommendations['motivation_message'])
                    except:
                        pass
        
        with tab2:
            show_dashboard()
    
    # Right sidebar for history
    if history_col:
        with history_col:
            render_history_content()

if __name__ == "__main__":
    main()
