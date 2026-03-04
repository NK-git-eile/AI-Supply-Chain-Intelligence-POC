import streamlit as st
from neo4j import GraphDatabase
import anthropic
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="AI Operations Intelligence", page_icon="🔗", layout="wide")

# Password Protection
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); padding: 2rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 2rem;'>
        <h1>🤖 AI Operations Intelligence</h1>
        <p>Berlin Manufacturing - Proof of Concept</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password = st.text_input("Enter Password:", type="password", key="password_input")
        if st.button("Login", use_container_width=True):
            if password == st.secrets.get("APP_PASSWORD", "bausch2026"):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Incorrect password")
    st.stop()

# Interactive Intro Slides
if 'show_intro' not in st.session_state:
    st.session_state.show_intro = True
if 'intro_page' not in st.session_state:
    st.session_state.intro_page = 1

if st.session_state.show_intro:
    
    # Slide 1: Data Overview
    if st.session_state.intro_page == 1:
        st.markdown("## 👋 Welcome to AI Operations Intelligence")
        st.markdown("""
        <div style='background: #f0f4ff; border-left: 4px solid #3b82f6; padding: 0.75rem 1rem; border-radius: 4px; margin-bottom: 0.75rem;'>
            <span style='font-size: 1.1rem;'>A proof of concept demonstrating <strong>AI-enabled insights on live manufacturing data</strong>. This capability could evolve into a full Production Control Tower with KPIs, root cause analysis, and Appian workflow integration to ensure <strong>PLANS are realized through ALIGNED EXECUTION</strong>.</span>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("""
            ### 📊 Live Berlin Manufacturing Data
            **Data Source:** Blue Yonder Production Plan  
            **Plan Date:** February 28, 2026 (Last Friday)
            
            **Production Data:** Schedules, resources, methods & steps  
            **Master Data:** Items, customers, must-win flags  
            **Inventory Data:** On-hand levels, quarantine status, available vs. reserved
            """)
        
        with col2:
            st.markdown("""
            ### ⚠️ Important Notice
            **Real Data:** ✅ Production schedules, inventory, customer orders, line assignments, production methods
            
            **Mock Data (Demo Only):** ⚠️ ASP, COGS, margin calculations
            
            📌 *"High margin" is defined as margin > 40% (`margin_pct > 0.40`)*
            
            *Financial figures are placeholder values for demonstration purposes.*
            """)
        
        st.markdown("""
        <div style='background: #e0f2fe; border-left: 4px solid #0284c7; padding: 0.5rem 0.8rem; border-radius: 4px; margin-top: 0.5rem; margin-bottom: 0.5rem; text-align: center;'>
            💬 <strong>We want your feedback!</strong> This is a proof of concept — use the <strong>Feedback</strong> section in the left sidebar to share your thoughts.
        </div>
        """, unsafe_allow_html=True)
        
        col_btn1, col_btn2, col_btn3, col_btn4, col_btn5 = st.columns([1, 1, 1, 1, 1])
        with col_btn2:
            if st.button("Next: How It Works →", use_container_width=True, type="primary"):
                st.session_state.intro_page = 2
                st.rerun()
        with col_btn4:
            if st.button("Skip Intro", use_container_width=True):
                st.session_state.show_intro = False
                st.rerun()
    
    # Slide 2: How Queries Work
    elif st.session_state.intro_page == 2:
        st.markdown("## 🤖 How AI Queries Work")
        
        # Visual flow
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div style='background: #dbeafe; border-radius: 8px; padding: 0.6rem 0.8rem;'>
                <strong>1️⃣ You Ask</strong><br>
                💬 Natural language question
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style='background: #e0e7ff; border-radius: 8px; padding: 0.6rem 0.8rem;'>
                <strong>2️⃣ AI Generates</strong><br>
                🔄 Cypher query created
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div style='background: #d1fae5; border-radius: 8px; padding: 0.6rem 0.8rem;'>
                <strong>3️⃣ Data Returns</strong><br>
                📊 Real-time results
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div style='background: #fef9c3; border-radius: 8px; padding: 0.6rem 0.8rem;'>
                <strong>4️⃣ AI Interprets</strong><br>
                💡 Business insight
            </div>
            """, unsafe_allow_html=True)
        
        # Interactive example - collapsed by default to save space
        with st.expander("🔍 See an Example Query"):
            st.markdown("""
            <div style='background: #dbeafe; border-left: 4px solid #3b82f6; padding: 0.4rem 0.8rem; border-radius: 4px; margin-bottom: 0.5rem;'>
                <strong>Step 1 — You Ask:</strong> <em>"Which high-margin products are starting on Line 5 this week?"</em>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("""
            <div style='background: #e0e7ff; border-left: 4px solid #6366f1; padding: 0.4rem 0.8rem; border-radius: 4px; margin-bottom: 0.3rem;'>
                <strong>Step 2 — AI Generates:</strong>
            </div>
            """, unsafe_allow_html=True)
            
            st.code("""MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: 'TFS 80/2 (Linie 5 NEU)'})
MATCH (sr)-[:FOR_ITEM]->(i:Item)
WHERE sr.start_date IN ['2-Mar-26', '3-Mar-26', ...] AND i.margin_pct > 0.40
RETURN sr.item, i.description, sr.quantity""", language="cypher")
            
            st.markdown("""
            <div style='background: #d1fae5; border-left: 4px solid #10b981; padding: 0.4rem 0.8rem; border-radius: 4px; margin-bottom: 0.5rem;'>
                <strong>Step 3 — Data Returns:</strong> 8 products across 9 work orders
            </div>
            <div style='background: #fef9c3; border-left: 4px solid #eab308; padding: 0.4rem 0.8rem; border-radius: 4px;'>
                <strong>Step 4 — AI Interprets:</strong> 💡 <em>"8 high-margin products, 9 work orders, $3.35M margin"</em>
            </div>
            """, unsafe_allow_html=True)
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        with col_btn1:
            if st.button("← Back", use_container_width=True):
                st.session_state.intro_page = 1
                st.rerun()
        with col_btn2:
            if st.button("Next: Quick Start →", use_container_width=True, type="primary"):
                st.session_state.intro_page = 3
                st.rerun()
        with col_btn3:
            if st.button("Skip Intro", use_container_width=True):
                st.session_state.show_intro = False
                st.rerun()
    
    # Slide 3: Quick Start
    elif st.session_state.intro_page == 3:
        st.markdown("## 🚀 Quick Start Guide")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 💬 Ask Questions
            
            **Choose from 4 categories:**
            - 📊 Financial Analysis
            - 👥 Customer Impact
            - ⏰ Scenario Planning
            - 🔧 Operations
            
            Or type your own question!
            """)
        
        with col2:
            st.markdown("""
            ### 🚨 Line Downtime Simulator
            
            **Test scenarios:**
            - Select a production line
            - Click "Simulate 3-Day Downtime"
            - See instant impact analysis
            - Get prioritized recommendations
            """)
        
        st.markdown("---")
        
        st.markdown("""
        <div style='background: #f0f4ff; border-left: 4px solid #6366f1; padding: 0.75rem 1rem; border-radius: 4px; margin-bottom: 0.75rem;'>
            <span style='font-size: 1.1rem;'><strong>🔮 Future Vision:</strong> Evolve this PoC into a full <strong>AI-enabled Control Tower</strong> with live KPIs, root cause analysis, and Appian workflows to execute recommended actions — ensuring <strong>planning and execution are in synch</strong>.</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style='background: #d1fae5; border-radius: 6px; padding: 0.5rem 0.8rem;'>
            ✅ <strong>You're Ready!</strong> Select a question category or use the simulator to explore line downtime scenarios. Share feedback via the sidebar.
        </div>
        <div style='margin-bottom: 1rem;'></div>
        """, unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns([1, 2])
        with col_btn1:
            if st.button("← Back", use_container_width=True):
                st.session_state.intro_page = 2
                st.rerun()
        with col_btn2:
            if st.button("🎯 Start Exploring", use_container_width=True, type="primary"):
                st.session_state.show_intro = False
                st.rerun()
    
    st.stop()  # Don't show main app until intro complete

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 0.75rem 1.5rem;
        border-radius: 8px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .main-header h1 {
        font-size: 1.75rem;
        margin: 0;
        padding: 0;
    }
    .main-header p {
        font-size: 0.9rem;
        margin: 0.25rem 0 0 0;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ Configuration")
    neo4j_uri = st.text_input("Neo4j URI", value=st.secrets.get("NEO4J_URI", ""), type="password")
    neo4j_user = "neo4j"
    neo4j_password = st.text_input("Neo4j Password", type="password", value=st.secrets.get("NEO4J_PASSWORD", ""))
    claude_key = st.text_input("Claude API Key", type="password", value=st.secrets.get("CLAUDE_API_KEY", ""))
    
    st.markdown("---")
    
    # Feedback Form
    st.subheader("💬 Feedback")
    st.markdown("*Your input helps us improve this tool!*")
    if 'feedback_key' not in st.session_state:
        st.session_state.feedback_key = 0
    feedback = st.text_area("Share your thoughts:", height=100, key=f"feedback_text_{st.session_state.feedback_key}", placeholder="What works well? What could be better?")
    
    if st.button("Submit Feedback", use_container_width=True):
        if feedback:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if 'all_feedback' not in st.session_state:
                st.session_state.all_feedback = []
            
            st.session_state.all_feedback.append({
                'timestamp': timestamp,
                'feedback': feedback
            })
            
            # Save to Neo4j for persistent storage
            try:
                if neo4j_uri and neo4j_password:
                    fb_driver = GraphDatabase.driver(neo4j_uri, auth=("neo4j", neo4j_password))
                    with fb_driver.session() as fb_session:
                        fb_session.run("""
                            CREATE (f:Feedback {
                                text: $text,
                                timestamp: $timestamp,
                                source: 'streamlit_app'
                            })
                        """, text=feedback, timestamp=timestamp)
                    fb_driver.close()
            except Exception:
                pass  # Don't block the user if Neo4j write fails
            
            st.session_state.feedback_key += 1
            st.success("✅ Thank you! Feedback submitted.")
            st.rerun()
            
            # Show recent feedback
            if len(st.session_state.all_feedback) > 0:
                with st.expander(f"📝 Feedback Log ({len(st.session_state.all_feedback)} items)"):
                    for item in reversed(st.session_state.all_feedback[-5:]):  # Show last 5
                        st.text(f"{item['timestamp']}")
                        st.text(f"{item['feedback'][:100]}...")
                        st.markdown("---")
        else:
            st.error("Please enter feedback")
    
    st.markdown("---")
    if st.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.rerun()

current_time = datetime.now()
st.markdown(f"""
<div class="main-header">
    <h1>🤖 AI Operations Intelligence - Berlin</h1>
    <p>{current_time.strftime('%B %d, %Y')} | {current_time.strftime('%H:%M')} CET</p>
</div>
""", unsafe_allow_html=True)

# Prominent Mock Data Warning
st.warning("⚠️ **DEMO DATA NOTICE:** This dashboard uses real production schedules and inventory from Berlin manufacturing (Blue Yonder plan dated Feb 28, 2026). **Financial data (ASP, COGS, margin) are mock values for demonstration purposes only.**")

if not all([neo4j_uri, neo4j_password]):
    st.warning("⚠️ Configure credentials in sidebar")
    st.stop()

driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

# This week dates (March 2-8, 2026 - Calendar week Mon-Sun)
THIS_WEEK = ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']

# ----- CACHED DATA FUNCTIONS (run once, not on every rerun) -----
@st.cache_data(ttl=300, show_spinner=False)
def get_kpis(_driver, week):
    """Cache KPI queries for 5 minutes to avoid re-running on every interaction."""
    with _driver.session() as session:
        starting = session.run("""
            MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item)
            WHERE sr.start_date IN $week AND i.item_type IN ['FP', 'SFP']
            RETURN sum(sr.quantity * i.asp) AS revenue, count(DISTINCT sr) AS orders
        """, week=week).single()
        
        must_win = session.run("""
            MATCH (sr:ScheduledReceipt)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c:Customer {must_win: true})
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            WHERE sr.start_date IN $week AND i.item_type IN ['FP', 'SFP']
            RETURN sum(sr.quantity * i.asp) AS value, count(DISTINCT c) AS customers
        """, week=week).single()
        
        high_margin = session.run("""
            MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item)
            WHERE i.margin_pct > 0.40 AND i.item_type IN ['FP', 'SFP']
            RETURN sum(sr.quantity * i.margin) AS margin
        """).single()
        
        active_lines = session.run("""
            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource)
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            WHERE i.item_type IN ['FP', 'SFP']
            RETURN count(DISTINCT r.line_name) AS total
        """).single()
    
    return (
        dict(starting) if starting else {'revenue': 0, 'orders': 0},
        dict(must_win) if must_win else {'value': 0, 'customers': 0},
        dict(high_margin) if high_margin else {'margin': 0},
        dict(active_lines) if active_lines else {'total': 0},
    )

@st.cache_data(ttl=300, show_spinner=False)
def get_line_data(_driver):
    """Cache line data for simulator dropdown."""
    with _driver.session() as session:
        lines_result = session.run("""
            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource)
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            WHERE i.item_type IN ['FP', 'SFP']
            RETURN r.line_name AS line,
                   count(sr) AS orders,
                   sum(sr.quantity * i.asp) AS revenue
            ORDER BY revenue DESC
            LIMIT 10
        """)
        return [(row['line'], row['orders'], row['revenue']) for row in lines_result]

# KPIs (cached - only hits Neo4j once per 5 minutes)
starting, must_win, high_margin, active_lines = get_kpis(driver, tuple(THIS_WEEK))

col1, col2, col3, col4 = st.columns(4)

revenue = starting.get('revenue') or 0
orders = starting.get('orders') or 0
col1.metric("This Week", f"${revenue/1e6:.1f}M", f"{orders} orders")

mw_value = must_win.get('value') or 0
mw_custs = must_win.get('customers') or 0
col2.metric("Must-Win", f"${mw_value/1e6:.1f}M", f"{mw_custs} customers")

hm_margin = high_margin.get('margin') or 0
col3.metric("High-Margin", f"${hm_margin/1e6:.1f}M", ">40%")

lines_count = active_lines.get('total') or 0
col4.metric("Lines", f"{lines_count}", "Active")

# Two columns
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("💬 Ask Questions")
    
    # Question categories with dropdowns
    st.markdown("**💡 Select a category, then choose a question:**")
    
    # Initialize session state
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = None
    if 'selected_question' not in st.session_state:
        st.session_state.selected_question = ""
    
    # Define question categories
    question_categories = {
        "📊 Financial Analysis": [
            "Which high-margin products are starting on Line 5 this week?",
            "Show me the highest margin work order starting on Line 5 this week",
            "What is the total revenue scheduled on Line 5 this week?"
        ],
        "👥 Customer Impact": [
            "Which customer orders depend on Line 5 production this week?",
            "Are any must-win customers affected by Line 5 this week?",
            "Show all must-win customer orders"
        ],
        "⏰ Scenario Planning": [
            "If Line 5 goes down Thursday and Friday, what revenue is at risk?",
            "If production is running ahead of schedule on Line 5, which order should we pull into this week?",
            "What happens if item 01742BAL cannot run on Line 5 this week?"
        ],
        "🔧 Operations": [
            "Which other lines can make the products scheduled on Line 5 this week?",
            "How many work orders start on Line 5 this week?",
            "Which production line has the most revenue this week?",
            "List all work orders starting on Line 5 this week"
        ]
    }
    
    # Pre-built Cypher queries for dropdown questions (skip AI entirely)
    PREBUILT_QUERIES = {
        "Which high-margin products are starting on Line 5 this week?": """
            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: 'TFS 80/2 (Linie 5 NEU)'})
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            WHERE sr.start_date IN ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']
              AND i.item_type IN ['FP', 'SFP'] AND i.margin_pct > 0.40
            RETURN sr.item, i.description, sr.start_date, sr.quantity, i.margin_pct, i.margin,
                   round(sr.quantity * i.margin) AS total_margin
            ORDER BY i.margin_pct DESC
            LIMIT 100""",
        
        "Show me the highest margin work order starting on Line 5 this week": """
            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: 'TFS 80/2 (Linie 5 NEU)'})
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            WHERE sr.start_date IN ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']
              AND i.item_type IN ['FP', 'SFP']
            RETURN sr.item, i.description, sr.start_date, sr.quantity, i.margin_pct, i.margin,
                   round(sr.quantity * i.margin) AS total_margin
            ORDER BY sr.quantity * i.margin DESC
            LIMIT 1""",
        
        "What is the total revenue scheduled on Line 5 this week?": """
            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: 'TFS 80/2 (Linie 5 NEU)'})
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            WHERE sr.start_date IN ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']
              AND i.item_type IN ['FP', 'SFP']
            RETURN sum(sr.quantity * i.asp) AS total_revenue, count(sr) AS work_orders, count(DISTINCT i) AS products
            LIMIT 100""",
        
        "Which customer orders depend on Line 5 production this week?": """
            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: 'TFS 80/2 (Linie 5 NEU)'})
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            MATCH (sr)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c:Customer)
            WHERE sr.start_date IN ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']
              AND i.item_type IN ['FP', 'SFP']
            RETURN c.customer_number, c.must_win, sr.item, i.description, sr.start_date, sr.quantity,
                   round(sr.quantity * i.asp) AS revenue
            ORDER BY c.must_win DESC, revenue DESC
            LIMIT 100""",
        
        "Are any must-win customers affected by Line 5 this week?": """
            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: 'TFS 80/2 (Linie 5 NEU)'})
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            MATCH (sr)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c:Customer {must_win: true})
            WHERE sr.start_date IN ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']
              AND i.item_type IN ['FP', 'SFP']
            RETURN c.customer_number, sr.item, i.description, sr.start_date, sr.quantity,
                   round(sr.quantity * i.asp) AS revenue, round(sr.quantity * i.margin) AS margin
            ORDER BY revenue DESC
            LIMIT 100""",
        
        "Show all must-win customer orders": """
            MATCH (sr:ScheduledReceipt)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c:Customer {must_win: true})
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            WHERE i.item_type IN ['FP', 'SFP']
            RETURN c.customer_number, sr.item, i.description, sr.start_date, sr.quantity,
                   round(sr.quantity * i.asp) AS revenue
            ORDER BY revenue DESC
            LIMIT 100""",
        
        "If Line 5 goes down Thursday and Friday, what revenue is at risk?": """
            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: 'TFS 80/2 (Linie 5 NEU)'})
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            WHERE sr.start_date IN ['5-Mar-26', '6-Mar-26'] AND i.item_type IN ['FP', 'SFP']
            RETURN sr.item, i.description, sr.start_date, sr.quantity,
                   round(sr.quantity * i.asp) AS revenue, round(sr.quantity * i.margin) AS margin
            ORDER BY revenue DESC
            LIMIT 100""",
        
        "If production is running ahead of schedule on Line 5, which order should we pull into this week?": """
            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: 'TFS 80/2 (Linie 5 NEU)'})
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            WHERE NOT sr.start_date IN ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']
              AND i.item_type IN ['FP', 'SFP']
            OPTIONAL MATCH (sr)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c:Customer)
            WITH sr, i, c,
                 CASE WHEN c.must_win = true THEN 1 ELSE 0 END AS is_must_win,
                 round(sr.quantity * i.asp) AS revenue,
                 round(sr.quantity * i.margin) AS margin
            RETURN sr.item, i.description, sr.start_date, sr.sched_date, sr.quantity,
                   revenue, margin, i.margin_pct,
                   CASE WHEN is_must_win = 1 THEN 'YES' ELSE 'NO' END AS must_win_customer,
                   c.customer_number AS customer
            ORDER BY is_must_win DESC, margin DESC
            LIMIT 20""",
        
        "What happens if item 01742BAL cannot run on Line 5 this week?": """
            MATCH (sr:ScheduledReceipt {item: '01742BAL'})-[:ON_RESOURCE]->(r:Resource {line_name: 'TFS 80/2 (Linie 5 NEU)'})
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            WHERE sr.start_date IN ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']
            OPTIONAL MATCH (sr2:ScheduledReceipt {item: '01742BAL'})-[:ON_RESOURCE]->(r2:Resource)
            WHERE r2.line_name <> 'TFS 80/2 (Linie 5 NEU)'
            RETURN sr.item, i.description, sr.start_date, sr.quantity,
                   round(sr.quantity * i.asp) AS revenue_at_risk,
                   collect(DISTINCT r2.line_name) AS alternative_lines
            LIMIT 100""",
        
        "Which other lines can make the products scheduled on Line 5 this week?": """
            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: 'TFS 80/2 (Linie 5 NEU)'})
            WHERE sr.start_date IN ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']
            WITH collect(DISTINCT sr.item) AS items
            UNWIND items AS item
            MATCH (sr2:ScheduledReceipt {item: item})-[:ON_RESOURCE]->(r2:Resource)
            WHERE r2.line_name <> 'TFS 80/2 (Linie 5 NEU)'
            RETURN item, collect(DISTINCT r2.line_name) AS alternative_lines
            LIMIT 100""",
        
        "How many work orders start on Line 5 this week?": """
            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: 'TFS 80/2 (Linie 5 NEU)'})
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            WHERE sr.start_date IN ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']
              AND i.item_type IN ['FP', 'SFP']
            RETURN count(sr) AS work_orders_count
            LIMIT 100""",
        
        "Which production line has the most revenue this week?": """
            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource)
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            WHERE sr.start_date IN ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']
              AND i.item_type IN ['FP', 'SFP']
            RETURN r.line_name, count(sr) AS work_orders, sum(sr.quantity * i.asp) AS total_revenue
            ORDER BY total_revenue DESC
            LIMIT 100""",
        
        "List all work orders starting on Line 5 this week": """
            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: 'TFS 80/2 (Linie 5 NEU)'})
            MATCH (sr)-[:FOR_ITEM]->(i:Item)
            WHERE sr.start_date IN ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']
              AND i.item_type IN ['FP', 'SFP']
            RETURN sr.item, i.description, sr.start_date, sr.sched_date, sr.quantity, i.item_type,
                   round(sr.quantity * i.asp) AS revenue
            ORDER BY sr.start_date, sr.item
            LIMIT 100""",
    }
    
    # Category buttons
    col_cat1, col_cat2 = st.columns(2)
    categories = list(question_categories.keys())
    
    for idx, category in enumerate(categories):
        target_col = col_cat1 if idx % 2 == 0 else col_cat2
        with target_col:
            if st.button(category, key=f"cat_{idx}", use_container_width=True):
                st.session_state.selected_category = category
    
    # Show dropdown if category selected
    if st.session_state.selected_category:
        st.markdown(f"**{st.session_state.selected_category}**")
        questions = question_categories[st.session_state.selected_category]
        
        selected_from_dropdown = st.selectbox(
            "Choose a question:",
            ["Select a question..."] + questions,
            index=0
        )
        
        if selected_from_dropdown != "Select a question...":
            st.session_state.selected_question = selected_from_dropdown
            st.session_state.selected_category = None
            st.session_state.question_key = st.session_state.get('question_key', 0) + 1
            st.session_state.ai_result_data = None
            st.session_state.ai_result_query = None
            st.session_state.ai_result_insight = None
            st.session_state.ai_result_empty_msg = None
            st.session_state.auto_run = True
            st.rerun()
    
    # Initialize text area key counter for resetting
    if 'question_key' not in st.session_state:
        st.session_state.question_key = 0
    
    # If a dropdown question was just selected, set it as the default
    default_question = st.session_state.get('selected_question', '')
    
    # Question text area with key for proper reset control
    question = st.text_area(
        "Your Question:", 
        height=100, 
        value=default_question,
        key=f"question_input_{st.session_state.question_key}",
        placeholder="Select a category above or type your own question..."
    )
    
    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
    with col_btn1:
        ask_button = st.button("🔍 Ask AI", use_container_width=True, type="primary")
    with col_btn2:
        show_query = st.checkbox("Show query", value=False)
    with col_btn3:
        clear_button = st.button("🔄 Clear", use_container_width=True)
    
    # Handle clear button
    if clear_button:
        st.session_state.selected_question = ""
        st.session_state.selected_category = None
        st.session_state.question_key += 1
        st.session_state.ai_result_data = None
        st.session_state.ai_result_query = None
        st.session_state.ai_result_insight = None
        st.session_state.ai_result_empty_msg = None
        st.rerun()

# Store results in session state so we can render below
if 'ai_result_data' not in st.session_state:
    st.session_state.ai_result_data = None
    st.session_state.ai_result_query = None
    st.session_state.ai_result_insight = None
    st.session_state.ai_result_empty_msg = None

with col_left:
    # Auto-run from dropdown selection or manual Ask AI
    should_run = False
    if st.session_state.get('auto_run') and question and all([neo4j_uri, neo4j_password, claude_key]):
        should_run = True
        st.session_state.auto_run = False
    elif ask_button and question and all([neo4j_uri, neo4j_password, claude_key]):
        should_run = True
    
    if should_run:
        # Log usage to session state
        if 'usage_log' not in st.session_state:
            st.session_state.usage_log = []
        
        st.session_state.usage_log.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'question': question
        })
        
        # Reset previous results
        st.session_state.ai_result_data = None
        st.session_state.ai_result_query = None
        st.session_state.ai_result_insight = None
        st.session_state.ai_result_empty_msg = None
        
        with st.spinner("Analyzing..."):
            try:
                client = anthropic.Anthropic(api_key=claude_key)
                
                # Check for pre-built query first (instant, no AI call needed)
                prebuilt = PREBUILT_QUERIES.get(question.strip())
                
                if prebuilt:
                    query = prebuilt.strip()
                else:
                    # Free-form question: use Haiku for fast query generation
                    response = client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=1200,
                        messages=[{"role": "user", "content": f"""You are a Neo4j Cypher query expert. Write a query to answer this question.

CRITICAL DATABASE FACTS:
1. Dates are STRINGS in format 'D-MMM-YY' (e.g., '1-Mar-26', '15-Apr-26')
2. NEVER use date() functions - they don't work with string dates
3. Line names must be EXACT matches - use the LINE NAME MAPPING below
4. "orders" or "work orders" = ScheduledReceipts (production jobs)
5. Include BOTH FP (finished products) and SFP (semi-finished products)
6. ScheduledReceipts don't have a single WO number - identify by item + start_date + quantity

SCHEMA:

Nodes:
- ScheduledReceipt: item (string), site (string), start_date (string), sched_date (string), quantity (float), line (string - production method)
- Resource: line_name (string - physical line), code (string), site (string)
- Item: code (string), item_type (string: 'FP' or 'SFP'), asp (float), margin (float), margin_pct (float - DECIMAL format: 0.40 = 40%, 0.25 = 25%. NEVER use integer percentages like 40 or 25), description (string)
- Customer: customer_number (string), must_win (boolean), country (string - UPPERCASE. ALL country values are stored in UPPERCASE e.g. 'GERMANY', 'UNITED ARAB EMIRATES', 'SAUDI ARABIA'. NEVER use mixed case like 'Germany' or 'Saudi Arabia'. Available countries: ALGERIA, ARGENTINA, AUSTRALIA, AUSTRIA, BAHRAIN, BELGIUM, BRAZIL, CANADA, CHINA, CYPRUS, CZECH REPUBLIC, DENMARK, EGYPT, FAROE ISLANDS, FINLAND, FRANCE VC, FRENCH GUIAN, GERMANY, GREECE, GUADELOUPE, IRAN (ISLAMIC REPL O, IRAQ, ISRAEL, ITALY, JORDAN, KUWAIT, LIBYAN ARAB, LUXEMBOURG, MALAYSIA, MARTINIQUE, MAURITIUS, MAYOTTE, MEXICO, MOROCCO, N. IRELAND, NETHERLANDS, NEW CALEDONI, NORWAY, POLAND, PORTUGAL, REPUBLIC OF KOREA, REUNION, SAUDI ARABIA, SINGAPORE, SOUTH AFRICA, SPAIN, SWEDEN, SWITZERLAND, TAIWAN, THAILAND, TUNISIA, TURKEY, UKRAINE, UNITED ARAB EMIRATES, UNITED KINGDOM, VIET NAM)
- Inventory: quantity (float), is_quarantine (boolean)

Relationships (CRITICAL - only these relationships exist, no others):
- (ScheduledReceipt)-[:ON_RESOURCE]->(Resource)
- (ScheduledReceipt)-[:FOR_ITEM]->(Item)        ← ONLY ScheduledReceipt connects to Item, NOT Customer or CustomerOrder
- (ScheduledReceipt)-[:FULFILLS]->(CustomerOrder)-[:FOR_CUSTOMER]->(Customer)
- (Inventory)-[:FOR_ITEM]->(Item)

COMMON QUERY PATTERNS (follow these exactly):
- To get items with customer info:
  MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item)
  MATCH (sr)-[:FULFILLS]->(co:CustomerOrder)-[:FOR_CUSTOMER]->(c:Customer)
- To get items with line info:
  MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item)
  MATCH (sr)-[:ON_RESOURCE]->(r:Resource)
- NEVER write (Customer)-[:FOR_ITEM] or (CustomerOrder)-[:FOR_ITEM] — these relationships do NOT exist

VALUE FORMAT RULES (CRITICAL - follow exactly):
- margin_pct is a DECIMAL between 0 and 1. Example: 0.40 means 40%, 0.25 means 25%
- "high margin" means margin_pct > 0.40 (i.e., above 40%)
- NEVER write margin_pct > 20 or margin_pct > 40 — these are WRONG. Always use decimals like 0.20, 0.40
- asp and margin are dollar amounts per unit (floats)
- quantity is a float (number of units)

LINE NAME MAPPING (users refer to lines casually - ALWAYS use the EXACT string after the arrow):
- "Line 1" / "Linie 1" / "Bosch" / "Bosch 1"         → 'BOSCH 1 (Linie 1)'
- "Line 4" / "Linie 4" / "TFS 20"                      → 'TFS 20 (Linie 4)'
- "Line 5" / "Linie 5" / "TFS 80" / "Linie 5 NEU"     → 'TFS 80/2 (Linie 5 NEU)'
- "Line 6" / "Linie 6" / "EDO 1" / "EDO Konfektion 1"  → 'Linie 6 EDO-Konfektion. I'
- "Line 9" / "Linie 9"                                  → 'LINIE 9'
- "Line 11" / "Linie 11" / "EDO 2" / "EDO Konfektion 2" → 'Linie 11 EDO-Konfektion. II'
- "Rommelag 3" / "Bottelpack 3" / "Bottelpack III"      → 'ROMMELAG BOTTELPACK III'
- "Rommelag 4" / "Bottelpack 4" / "Bottelpack IV"       → 'ROMMELAG BOTTELPACK IV'
- "Aggregation" / "Aggregation 1"                        → 'AGGREGATIONSSTATION 1'

CRITICAL: NEVER use the casual name (e.g., "Line 5") in a Cypher query. ALWAYS substitute the exact database string (e.g., 'TFS 80/2 (Linie 5 NEU)').

THIS WEEK DATES (March 2-8, 2026 - Calendar week Mon-Sun):
['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']

DATE MAPPING (for relative date references):
- Today = March 3, 2026 (Tuesday)
- Monday = March 2, 2026 = '2-Mar-26'
- Tuesday = March 3, 2026 = '3-Mar-26'
- Wednesday = March 4, 2026 = '4-Mar-26'
- Thursday = March 5, 2026 = '5-Mar-26'
- Friday = March 6, 2026 = '6-Mar-26'
- Saturday = March 7, 2026 = '7-Mar-26'
- Sunday = March 8, 2026 = '8-Mar-26'

WORK ORDER IDENTIFICATION:
- Always return these fields to identify a work order: sr.item, sr.start_date, sr.quantity
- Optionally include: sr.sched_date, sr.site, i.description, i.item_type
- Do NOT expand to customer orders unless specifically asked
- One ScheduledReceipt can fulfill multiple CustomerOrders - don't join unless needed

NOW ANSWER THIS QUESTION: {question}

RULES:
- Return ONLY the Cypher query
- Use EXACT line names from the LINE NAME MAPPING above (the string AFTER the arrow)
- For dates, use IN clause with string list
- Include BOTH FP and SFP in item_type filters: i.item_type IN ['FP', 'SFP']
- Always include sr.item, sr.start_date, sr.quantity to identify work orders
- Don't join to CustomerOrders unless the question specifically asks about customers
- Add LIMIT 100 at the end
- No markdown formatting, just the query

Query:"""}]
                    )
                    
                    query = response.content[0].text.strip()
                    if '```' in query:
                        query = query.split('```')[1].replace('cypher','').strip()
                    
                    # ----- VALIDATION: Check for casual line names that slipped through -----
                    casual_to_exact = {
                        "'Line 1'": "'BOSCH 1 (Linie 1)'",
                        "'Line 4'": "'TFS 20 (Linie 4)'",
                        "'Line 5'": "'TFS 80/2 (Linie 5 NEU)'",
                        "'Line 6'": "'Linie 6 EDO-Konfektion. I'",
                        "'Line 9'": "'LINIE 9'",
                        "'Line 11'": "'Linie 11 EDO-Konfektion. II'",
                        '"Line 1"': "'BOSCH 1 (Linie 1)'",
                        '"Line 4"': "'TFS 20 (Linie 4)'",
                        '"Line 5"': "'TFS 80/2 (Linie 5 NEU)'",
                        '"Line 6"': "'Linie 6 EDO-Konfektion. I'",
                        '"Line 9"': "'LINIE 9'",
                        '"Line 11"': "'Linie 11 EDO-Konfektion. II'",
                        "'Linie 5'": "'TFS 80/2 (Linie 5 NEU)'",
                        "'Linie 1'": "'BOSCH 1 (Linie 1)'",
                        "'Linie 4'": "'TFS 20 (Linie 4)'",
                        "'Linie 6'": "'Linie 6 EDO-Konfektion. I'",
                        "'Linie 9'": "'LINIE 9'",
                        "'Linie 11'": "'Linie 11 EDO-Konfektion. II'",
                        '"Linie 5"': "'TFS 80/2 (Linie 5 NEU)'",
                        '"Linie 1"': "'BOSCH 1 (Linie 1)'",
                        '"Linie 4"': "'TFS 20 (Linie 4)'",
                        '"Linie 6"': "'Linie 6 EDO-Konfektion. I'",
                        '"Linie 9"': "'LINIE 9'",
                        '"Linie 11"': "'Linie 11 EDO-Konfektion. II'",
                        "line_name: 'Line 5'": "line_name: 'TFS 80/2 (Linie 5 NEU)'",
                        "line_name: 'Line 1'": "line_name: 'BOSCH 1 (Linie 1)'",
                        "line_name: 'Line 4'": "line_name: 'TFS 20 (Linie 4)'",
                        "line_name: 'Line 6'": "line_name: 'Linie 6 EDO-Konfektion. I'",
                        "line_name: 'Line 9'": "line_name: 'LINIE 9'",
                        "line_name: 'Line 11'": "line_name: 'Linie 11 EDO-Konfektion. II'",
                        "CONTAINS 'Line 5'": "= 'TFS 80/2 (Linie 5 NEU)'",
                        "CONTAINS 'Line 1'": "= 'BOSCH 1 (Linie 1)'",
                        "CONTAINS 'Line 4'": "= 'TFS 20 (Linie 4)'",
                        "CONTAINS 'Line 9'": "= 'LINIE 9'",
                        "CONTAINS 'Line 11'": "= 'Linie 11 EDO-Konfektion. II'",
                        "CONTAINS 'Line 6'": "= 'Linie 6 EDO-Konfektion. I'",
                        "CONTAINS '5'": "= 'TFS 80/2 (Linie 5 NEU)'",
                    }
                    
                    for casual, exact in casual_to_exact.items():
                        if casual in query:
                            query = query.replace(casual, exact)
                    
                    # ----- VALIDATION: Fix margin_pct integer values -----
                    import re
                    margin_pattern = re.compile(r'margin_pct\s*([><=!]+)\s*(\d+)(?!\.\d)')
                    def fix_margin(match):
                        operator = match.group(1)
                        value = int(match.group(2))
                        if value > 1:
                            return f'margin_pct {operator} {value / 100}'
                        return match.group(0)
                    query = margin_pattern.sub(fix_margin, query)
                    # ----- END VALIDATION -----
                
                # --- From here, runs for both prebuilt and free-form queries ---
                if show_query:
                    st.session_state.ai_result_query = query
                
                with driver.session() as session:
                    data = [dict(r) for r in session.run(query)]
                
                if data:
                    st.session_state.ai_result_data = pd.DataFrame(data)
                    
                    # AI interpretation of results (Haiku for speed)
                    with st.spinner("Interpreting results..."):
                        interpret_response = client.messages.create(
                            model="claude-haiku-4-5-20251001",
                            max_tokens=250,
                            messages=[{"role": "user", "content": f"""The user asked: "{question}"

The query returned {len(data)} results.

Sample of the data (first 20 rows):
{pd.DataFrame(data).head(20).to_string()}

Provide a brief, insightful summary answering the user's question. Focus on:
- Key numbers and totals
- Important patterns or insights
- Direct answer to what they asked

Be concise (2-3 sentences maximum). Use natural business language with proper spacing.

CRITICAL: Ensure proper spacing around all numbers and dollar amounts.
Good: "$2.74M in revenue" or "$2.74 M in revenue"
Bad: "2.74Minrevenue" or "$2.74Minrevenue"

Summary:"""}]
                        )
                        
                        summary = interpret_response.content[0].text.strip()
                        summary = summary.replace('$', ' $').replace('  ', ' ')
                        summary = ' '.join(summary.split())
                        st.session_state.ai_result_insight = summary
                    
                else:
                    interpret_response = client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=150,
                        messages=[{"role": "user", "content": f"""The user asked: "{question}"

The database query returned no results (0 rows).

The generated Cypher query was:
{query}

Provide a clear, direct answer to the user's question based on this empty result.

CRITICAL RULES:
- ONLY state what the query looked for and that it found nothing. Do NOT speculate about WHY.
- Do NOT make claims about other data that might or might not exist (e.g., don't say "there are no scheduled receipts on Line 5" just because a filtered query returned empty — the filter may be the reason, not the absence of data).
- Keep it to 1 sentence maximum.
- State the null result precisely: "No [exactly what was queried] were found for [exactly the filters applied]."

Examples of GOOD answers:
- "No must-win customer orders were found linked to Line 5 production this week."
- "No alternative production lines were found for these items."

Examples of BAD answers (never do this):
- "There are no scheduled receipts on Line 5 this week." (wrong — the query filtered on must-win, not all receipts)
- "Either no customers are marked as must-win, or none have orders." (speculative)

Answer:"""}]
                    )
                    
                    answer = interpret_response.content[0].text.strip()
                    st.session_state.ai_result_empty_msg = answer
                    
            except Exception as e:
                st.error(f"Error: {e}")

# ----- RENDER AI RESULTS BELOW ASK AI (full width under left column) -----
with col_left:
    if st.session_state.get('ai_result_insight'):
        st.info(f"💡 **Insight:** {st.session_state.ai_result_insight}")
    
    if st.session_state.get('ai_result_empty_msg'):
        st.success(f"✅ {st.session_state.ai_result_empty_msg}")
    
    if st.session_state.get('ai_result_query'):
        st.code(st.session_state.ai_result_query, language="cypher")
    
    if st.session_state.get('ai_result_data') is not None:
        st.dataframe(st.session_state.ai_result_data, use_container_width=True, height=300)

with col_right:
    st.subheader("🚨 Line Downtime Simulator")
    
    # Line data cached - no Neo4j call on every rerun
    line_data = get_line_data(driver)
    
    if line_data:
        line_options = [f"{line} — {orders} orders, ${rev/1e6:.1f}M" for line, orders, rev in line_data]
        selected_option = st.selectbox("", line_options, label_visibility="collapsed")
        selected_line = selected_option.split(" — ")[0]
        
        if st.button("🔧 Simulate 3-Day Downtime", use_container_width=True):
            with st.spinner("Analyzing..."):
                with driver.session() as session:
                    
                    total = session.run("""
                        MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                        MATCH (sr)-[:FOR_ITEM]->(i:Item)
                        WHERE i.item_type IN ['FP', 'SFP']
                        RETURN count(sr) AS orders,
                               count(DISTINCT i) AS products,
                               sum(sr.quantity * i.asp) AS revenue,
                               sum(sr.quantity * i.margin) AS margin
                    """, line=selected_line).single()
                    
                    if not total or total['orders'] == 0:
                        st.error("❌ No production found")
                    else:
                        with st.expander("🔍 Analysis Trail", expanded=True):
                            st.markdown("### 📊 TOTAL IMPACT (All Scheduled Orders)")
                            st.success(f"✓ {total['orders']} total work orders on this line")
                            st.write(f"   {total['products']} different products")
                            st.write(f"   ${total['revenue']/1e6:.1f}M revenue | ${total['margin']/1e6:.1f}M margin")
                            
                            st.markdown("---")
                            st.markdown("### ⏰ CRITICAL THIS WEEK (March 2-8)")
                            
                            this_week = session.run("""
                                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                                MATCH (sr)-[:FOR_ITEM]->(i:Item)
                                WHERE sr.start_date IN $week AND i.item_type IN ['FP', 'SFP']
                                RETURN count(sr) AS orders,
                                       sum(sr.quantity * i.asp) AS revenue,
                                       sum(sr.quantity * i.margin) AS margin
                            """, line=selected_line, week=THIS_WEEK).single()
                            
                            tw_orders = this_week['orders'] if this_week and this_week['orders'] else 0
                            tw_revenue = this_week['revenue'] if this_week and this_week['revenue'] else 0
                            tw_margin = this_week['margin'] if this_week and this_week['margin'] else 0
                            
                            st.info(f"📅 **{tw_orders} orders** starting this week (${tw_revenue/1e6:.1f}M revenue)")
                            
                            inv_check = session.run("""
                                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                                MATCH (sr)-[:FOR_ITEM]->(i:Item)
                                WHERE sr.start_date IN $week AND i.item_type IN ['FP', 'SFP']
                                OPTIONAL MATCH (inv:Inventory)-[:FOR_ITEM]->(i)
                                WHERE NOT inv.is_quarantine AND inv.quantity > 0
                                WITH sr, i, sum(COALESCE(inv.quantity, 0)) AS available
                                WITH count(DISTINCT CASE WHEN available > 0 THEN i.code END) AS with_stock,
                                     count(DISTINCT CASE WHEN available = 0 THEN i.code END) AS no_stock
                                RETURN with_stock, no_stock
                            """, line=selected_line, week=THIS_WEEK).single()
                            
                            if inv_check:
                                if inv_check['with_stock'] > 0:
                                    st.success(f"✅ **{inv_check['with_stock']} products** have available inventory")
                                if inv_check['no_stock'] > 0:
                                    st.error(f"🔴 **{inv_check['no_stock']} products** have NO inventory - must produce")
                            
                            mw = session.run("""
                                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                                MATCH (sr)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c:Customer {must_win: true})
                                MATCH (sr)-[:FOR_ITEM]->(i:Item)
                                WHERE sr.start_date IN $week AND i.item_type IN ['FP', 'SFP']
                                RETURN count(DISTINCT c) AS count,
                                       collect(DISTINCT c.customer_number)[0..3] AS ids,
                                       sum(sr.quantity * i.margin) AS margin
                            """, line=selected_line, week=THIS_WEEK).single()
                            
                            if mw and mw['count'] > 0:
                                st.error(f"🔴 **{mw['count']} must-win customers** affected this week")
                                st.write(f"   Customer IDs: {', '.join(mw['ids'])}")
                                st.write(f"   Margin: ${mw['margin']/1e3:.0f}K")
                            else:
                                st.success("✅ No must-win customers starting this week")
                            
                            hm = session.run("""
                                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                                MATCH (sr)-[:FOR_ITEM]->(i:Item)
                                WHERE sr.start_date IN $week
                                  AND i.item_type IN ['FP', 'SFP']
                                  AND i.margin_pct > 0.40
                                RETURN count(DISTINCT i) AS products,
                                       sum(sr.quantity * i.margin) AS margin
                            """, line=selected_line, week=THIS_WEEK).single()
                            
                            if hm and hm['products'] > 0:
                                st.warning(f"💎 **{hm['products']} high-margin products** starting this week (${hm['margin']/1e6:.1f}M)")
                            else:
                                st.info("Standard margin products this week")
                            
                            alt = session.run("""
                                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                                WHERE sr.start_date IN $week
                                WITH collect(DISTINCT sr.item) AS items
                                UNWIND items AS item
                                MATCH (sr2:ScheduledReceipt {item: item})-[:ON_RESOURCE]->(r2:Resource)
                                WHERE r2.line_name <> $line
                                RETURN count(DISTINCT r2.line_name) AS count,
                                       collect(DISTINCT r2.line_name)[0..3] AS lines
                            """, line=selected_line, week=THIS_WEEK).single()
                            
                            if alt and alt['count'] > 0:
                                st.success(f"🔧 **{alt['count']} alternative lines** found")
                                st.write(f"   Options: {', '.join(alt['lines'])}")
                            else:
                                st.error("❌ No alternative lines - products are line-specific")
                        
                        st.markdown("---")
                        st.markdown("### 📋 Impact Summary")
                        
                        col_sum1, col_sum2 = st.columns(2)
                        
                        with col_sum1:
                            st.markdown("**Total Exposure:**")
                            st.write(f"Orders: {total['orders']}")
                            st.write(f"Revenue: ${total['revenue']/1e6:.1f}M")
                            st.write(f"Margin: ${total['margin']/1e6:.1f}M")
                        
                        with col_sum2:
                            st.markdown("**Critical This Week:**")
                            st.write(f"Orders: {tw_orders}")
                            st.write(f"Revenue: ${tw_revenue/1e6:.1f}M")
                            st.write(f"Margin: ${tw_margin/1e6:.1f}M")
                        
                        st.markdown("---")
                        st.markdown("### 💡 Recommended Actions")
                        
                        recs = []
                        if mw and mw['count'] > 0:
                            recs.append(f"1. 🔴 **URGENT:** Protect {mw['count']} must-win customers starting this week")
                        if inv_check and inv_check['no_stock'] > 0:
                            recs.append(f"2. 🔴 **CRITICAL:** {inv_check['no_stock']} products have NO inventory - cannot delay")
                        if inv_check and inv_check['with_stock'] > 0:
                            recs.append(f"3. ✅ **OPTION:** {inv_check['with_stock']} products can ship from available stock")
                        if hm and hm['products'] > 0:
                            recs.append(f"4. 💎 **PRIORITY:** Focus on {hm['products']} high-margin products (${hm['margin']/1e6:.1f}M)")
                        if alt and alt['count'] > 0:
                            recs.append(f"5. 🔧 **BACKUP:** {alt['count']} alternative lines available for some products")
                        else:
                            recs.append("5. ⚠️ **CONSTRAINT:** No alternative lines - must repair immediately")
                        
                        for rec in recs:
                            st.markdown(rec)

st.caption("AI Operations Intelligence - Berlin PoC | Blue Yonder data (Feb 28, 2026) + Mock financials | 🔒 Secure Access")
