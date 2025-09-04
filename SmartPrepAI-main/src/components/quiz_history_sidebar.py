import streamlit as st
from src.models.simple_session import SimpleSessionManager
import urllib.parse

def show_quiz_history_right_sidebar():
    """Display quiz history in a collapsible right sidebar"""
    if 'user' not in st.session_state or not st.session_state.user:
        return False
    
    # Toggle button for history visibility
    if 'show_history' not in st.session_state:
        st.session_state.show_history = False
    
    return st.session_state.get('show_history', False)

def render_history_content():
    """Render the actual history content"""
    session_manager = SimpleSessionManager()
    user_sessions = session_manager.get_user_sessions(st.session_state.user['id'], 15)
    
    st.markdown("### 📚 Quiz History")
    
    if not user_sessions:
        st.write("No previous quizzes")
        return
    
    # Search/filter functionality
    search_term = st.text_input("🔍 Search quizzes...", placeholder="Search by topic or date", key="history_search")
    
    # Filter sessions based on search
    if search_term:
        filtered_sessions = [
            session for session in user_sessions 
            if search_term.lower() in session['display_title'].lower() or 
               search_term.lower() in session['created_at'].lower()
        ]
    else:
        filtered_sessions = user_sessions
    
    # Group by date
    grouped_sessions = {}
    for session in filtered_sessions:
        date_key = session['short_date'] if session['short_date'] else "Unknown"
        if date_key not in grouped_sessions:
            grouped_sessions[date_key] = []
        grouped_sessions[date_key].append(session)
    
    # Display grouped sessions
    for date, sessions in sorted(grouped_sessions.items(), reverse=True):
        if date != "Unknown":
            st.markdown(f"**{date}**")
        
        for session in sessions:
            # Score indicator
            score = session.get('score', 0)
            if score >= 80:
                score_icon = "🟢"
            elif score >= 60:
                score_icon = "🟡" 
            else:
                score_icon = "🔴"
            
            # Create a container for each quiz
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Quiz title and info
                    title = session['display_title']
                    if len(title) > 25:
                        title = title[:25] + "..."
                    
                    st.markdown(f"**{score_icon} {title}**")
                    st.caption(f"{score:.0f}% • {session['difficulty']} • {session['num_questions']}Q")
                
                with col2:
                    if st.button("👁️", key=f"view_{session['id']}", help="Review quiz"):
                        st.session_state.viewing_quiz_id = session['id']
                        st.session_state.view_mode = 'revision'
                        st.rerun()
                
                st.markdown("---")

def show_revision_view(session_id: int):
    """Display quiz in read-only revision mode with backward compatibility"""
    session_manager = SimpleSessionManager()
    session_data = session_manager.get_complete_session(session_id)
    
    if not session_data:
        st.error("Quiz session not found!")
        return
    
    # Header with quiz info
    st.header(f"📖 Quiz Revision")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Topic", session_data.get('topic', 'General'))
    with col2:
        st.metric("Score", f"{session_data.get('score', 0):.1f}%")
    with col3:
        st.metric("Difficulty", session_data.get('difficulty', 'Medium'))
    with col4:
        st.metric("Date", session_data.get('created_at', '')[:10])
    
    # Back button
    if st.button("⬅️ Back to New Quiz", type="secondary"):
        if 'viewing_quiz_id' in st.session_state:
            del st.session_state.viewing_quiz_id
        if 'view_mode' in st.session_state:
            del st.session_state.view_mode
        st.rerun()
    
    st.markdown("---")
    
    # Get detailed data
    questions_data = session_data.get('questions_data', [])
    user_answers = session_data.get('user_answers', [])
    results_data = session_data.get('results_data', [])
    
    # Check if we have detailed data
    if not questions_data and not results_data:
        # No detailed data available for old quizzes
        st.info("📝 This is an older quiz session. Detailed question data is not available.")
        st.write(f"**Quiz Summary:**")
        st.write(f"- **Topic:** {session_data.get('topic', 'General')}")
        st.write(f"- **Sub-topic:** {session_data.get('sub_topic', 'None')}")
        st.write(f"- **Question Type:** {session_data.get('question_type', 'Multiple Choice')}")
        st.write(f"- **Difficulty:** {session_data.get('difficulty', 'Medium')}")
        st.write(f"- **Number of Questions:** {session_data.get('num_questions', 1)}")
        st.write(f"- **Score:** {session_data.get('score', 0):.1f}%")
        st.write(f"- **Date:** {session_data.get('created_at', '')}")
        
        st.info("💡 **Tip:** Take a new quiz to get detailed explanations and review capabilities!")
        return
    
    # Display detailed questions and results
    if not results_data and questions_data:
        # Reconstruct results if not stored (for older sessions)
        results_data = []
        for i, (q, user_ans) in enumerate(zip(questions_data, user_answers)):
            is_correct = False
            if q.get('type') == 'MCQ':
                is_correct = user_ans == q.get("correct_answer")
            else:
                is_correct = user_ans.strip().lower() == q.get('correct_answer', '').strip().lower()
            
            results_data.append({
                'question_number': i+1,
                'question': q.get('question', ''),
                'question_type': q.get("type", 'MCQ'),
                'user_answer': user_ans,
                'correct_answer': q.get("correct_answer", ''),
                'explanation': q.get('explanation', ''),
                'is_correct': is_correct,
                'options': q.get('options', [])
            })
    
    # Display each question with results
    for i, result in enumerate(results_data):
        st.subheader(f"Question {i+1}")
        
        # Question
        question_text = result.get('question', f'Question {i+1}')
        st.write(f"**{question_text}**")
        
        # Show options for MCQ
        if result.get('options'):
            st.write("**Options:**")
            for opt in result['options']:
                if opt == result.get('correct_answer'):
                    st.write(f"✅ {opt} (Correct Answer)")
                elif opt == result.get('user_answer'):
                    st.write(f"❌ {opt} (Your Answer)")
                else:
                    st.write(f"• {opt}")
        
        # Show answers
        if result.get('is_correct'):
            st.success(f"✅ **Your Answer:** {result.get('user_answer', 'N/A')} (Correct!)")
        else:
            st.error(f"❌ **Your Answer:** {result.get('user_answer', 'N/A')}")
            st.info(f"✅ **Correct Answer:** {result.get('correct_answer', 'N/A')}")
        
        # Show explanation if available
        if result.get('explanation'):
            st.info(f"💡 **Explanation:** {result['explanation']}")
        
        # AI links for further study
        st.write("**🤖 Study this concept further:**")
        topic = session_data.get('topic', 'General')
        
        query = f"Explain this {topic} concept in detail: '{question_text}' Answer: '{result.get('correct_answer', '')}'"
        encoded_query = urllib.parse.quote(query)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"[ChatGPT](https://chat.openai.com/?q={encoded_query})")
        with col2:
            st.markdown(f"[Gemini](https://gemini.google.com/?q={encoded_query})")
        with col3:
            st.markdown(f"[Claude](https://claude.ai/?q={encoded_query})")
        with col4:
            st.markdown(f"[Perplexity](https://www.perplexity.ai/?q={encoded_query})")
        
        st.markdown("---")
    
    # Summary
    if results_data:
        correct_count = sum(1 for result in results_data if result.get('is_correct', False))
        total_questions = len(results_data)
        
        st.subheader("📊 Quiz Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Score", f"{session_data.get('score', 0):.1f}%")
        with col2:
            st.metric("Correct", f"{correct_count}/{total_questions}")
        with col3:
            st.metric("Difficulty", session_data.get('difficulty', 'Medium'))
