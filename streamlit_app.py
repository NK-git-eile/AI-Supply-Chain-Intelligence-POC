import streamlit as st
from neo4j import GraphDatabase
import anthropic
import os
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Production Control Tower", page_icon="🔗", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .action-high {
        background: #fee2e2;
        border-left: 4px solid #dc2626;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .status-good { color: #10b981; font-weight: bold; }
    .status-warning { color: #f59e0b; font-weight: bold; }
    .status-critical { color: #dc2626; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Sidebar (simplified)
with st.sidebar:
    st.title("⚙️ Configuration")
    neo4j_uri = st.text_input("Neo4j URI", value=st.secrets.get("NEO4J_URI", ""), type="password")
    neo4j_user = "neo4j"
    neo4j_password = st.text_input("Neo4j Password", type="password", value=st.secrets.get("NEO4J_PASSWORD", ""))
    claude_key = st.text_input("Claude API Key", type="password", value=st.secrets.get("CLAUDE_API_KEY", ""))

# Hero Header
current_time = datetime.now()
st.markdown(f"""
<div class="main-header">
    <h1>🔗 PRODUCTION CONTROL TOWER</h1>
    <h3>Berlin Manufacturing Site</h3>
    <p style="font-size: 1.1rem; margin-top: 0.5rem;">
        {current_time.strftime('%A, %B %d, %Y')} | {current_time.strftime('%H:%M')} CET
    </p>
</div>
""", unsafe_allow_html=True)

# Refresh button
col1, col2 = st.columns([1, 5])
with col1:
    refresh = st.button("🔄 Refresh Data", use_container_width=True)

# Financial KPIs Section
if all([neo4j_uri, neo4j_password]):
    try:
        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        
        st.header("📊 PRODUCTION INTELLIGENCE - NEXT 7 DAYS")
        week_start = current_time.strftime('%Y-%m-%d')
        week_end = (current_time + timedelta(days=7)).strftime('%Y-%m-%d')
        st.markdown(f"**Planning Horizon:** {current_time.strftime('%B %d')} - {(current_time + timedelta(days=7)).strftime('%B %d, %Y')}")
        
        with driver.session() as session:
            # Calculate KPIs
            
            # Shipping this week (Finished Goods only)
            shipping = session.run("""
                MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                WHERE sr.sched_date >= $start AND sr.sched_date <= $end
                RETURN sum(sr.quantity * i.asp) AS revenue,
                       count(DISTINCT sr) AS orders
            """, start=week_start, end=week_end).single()
            
            # Must-win exposure
            must_win = session.run("""
                MATCH (sr:ScheduledReceipt)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c:Customer {must_win: true})
                MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                WHERE sr.sched_date >= $start AND sr.sched_date <= $end
                RETURN sum(sr.quantity * i.asp) AS value,
                       count(DISTINCT c) AS customers
            """, start=week_start, end=week_end).single()
            
            # High-margin products
            high_margin = session.run("""
                MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                WHERE i.margin_pct > 0.40
                RETURN sum(sr.quantity * i.margin) AS margin,
                       sum(sr.quantity) AS units
            """).single()
            
           # Work orders scheduled
work_orders = session.run("""
    MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
    RETURN count(sr) AS total
""").single()
            
            # Products scheduled
            products = session.run("""
                MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                WHERE sr.sched_date >= $start AND sr.sched_date <= $end
                RETURN count(DISTINCT i) AS count
            """, start=week_start, end=week_end).single()
            
            # Total volume
            volume = session.run("""
                MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                WHERE sr.sched_date >= $start AND sr.sched_date <= $end
                RETURN sum(sr.quantity) AS total
            """, start=week_start, end=week_end).single()
        
        driver.close()
        
        # Display KPIs in grid
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            revenue = shipping['revenue'] if shipping and shipping['revenue'] else 0
            orders = shipping['orders'] if shipping and shipping['orders'] else 0
            st.metric(
                "Shipping This Week",
                f"${revenue/1e6:.1f}M" if revenue > 0 else "$0",
                delta=f"{orders} orders"
            )
        
        with col2:
            mw_value = must_win['value'] if must_win and must_win['value'] else 0
            mw_custs = must_win['customers'] if must_win and must_win['customers'] else 0
            st.metric(
                "Must-Win Exposure",
                f"${mw_value/1e6:.1f}M" if mw_value > 0 else "$0",
                delta=f"{mw_custs} customers",
                delta_color="inverse"
            )
        
        with col3:
            hm_margin = high_margin['margin'] if high_margin and high_margin['margin'] else 0
            st.metric(
                "High-Margin Products",
                f"${hm_margin/1e6:.1f}M" if hm_margin > 0 else "$0",
                delta=">40% margin"
            )
        
        with col4:
    total_orders = work_orders['total'] if work_orders and work_orders['total'] else 0
    st.metric(
        "Work Orders",
        f"{total_orders:,}",
        delta="Scheduled"
    )
        
        # Second row
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            prod_count = products['count'] if products and products['count'] else 0
            st.metric(
                "Products Scheduled",
                f"{prod_count}",
                delta="Unique SKUs"
            )
        
        with col6:
            vol = volume['total'] if volume and volume['total'] else 0
            st.metric(
                "Order Volume",
                f"{vol:,.0f}" if vol > 0 else "0",
                delta="units/week"
            )
        
        with col7:
            avg_margin = (hm_margin / (high_margin['units'] * 10) * 100) if high_margin and high_margin['units'] else 0
            st.metric(
                "Avg Margin",
                f"{avg_margin:.1f}%" if avg_margin > 0 else "0%",
                delta="High-margin products"
            )
        
        with col8:
            st.metric(
                "Data Status",
                "✓ Live",
                delta="Mock financials"
            )
        
        st.markdown("---")
        
    except Exception as e:
        st.error(f"Error loading KPIs: {e}")
        st.info("Configure credentials in sidebar to view dashboard")

# Query Interface (your existing code)
st.header("💬 Interactive Query Interface")

st.markdown("""
Ask questions in plain English about your supply chain data. The AI will:
1. Write the appropriate database query
2. Execute it against your live data
3. Display the results
""")

# Sample questions
with st.expander("📋 Sample Questions You Can Ask"):
    st.markdown("""
    **Financial Analysis:**
    - What's the total margin for products shipping this week?
    - Show me high-margin products (>40%) scheduled this month
    - Which products have the highest revenue?
    
    **Production & Capacity:**
    - Show me all production lines
    - Which lines have the most scheduled work?
    - What's scheduled on finished goods lines?
    
    **Customer Analysis:**
    - Show me all must-win customers
    - Which customers have the most orders?
    - Show me customers with orders this week
    
    **Risk Analysis:**
    - What finished goods ship in next 48 hours?
    - Show me must-win customer orders
    - Which high-margin products are scheduled?
    """)

# Question input
question = st.text_area("Your question:", height=100, placeholder="e.g., Show me high-margin products shipping this week")

col1, col2 = st.columns([1, 4])

with col1:
    ask_button = st.button("🔍 Ask AI", type="primary", use_container_width=True)

with col2:
    show_query = st.checkbox("Show generated query", value=True)

if ask_button:
    if not question.strip():
        st.warning("Please enter a question")
    elif not all([neo4j_uri, neo4j_password, claude_key]):
        st.error("Please configure credentials in sidebar")
    else:
        with st.spinner("🤖 AI is processing your question..."):
            try:
                # Ask Claude to write query
                client = anthropic.Anthropic(api_key=claude_key)
                
                query_prompt = f"""You are a Neo4j Cypher query expert. Write a query to answer this question.

DATABASE SCHEMA:

Nodes:
- ScheduledReceipt: item, site, line, quantity, sched_date, start_date
- CustomerOrder: order_id, item, site, customer_number, country, ship_date, quantity
- Customer: customer_number, country, must_win (boolean)
- Item: code, description, item_type ('FP' or 'SFP'), family, asp, cogs, margin, margin_pct, strategic_importance, abc_class

Relationships:
- (ScheduledReceipt)-[:FULFILLS]->(CustomerOrder)-[:FOR_CUSTOMER]->(Customer)
- (ScheduledReceipt)-[:FOR_ITEM]->(Item)

IMPORTANT:
1. Return ONLY the Cypher query
2. For financial data, use Item node properties (asp, margin, margin_pct)
3. Filter to item_type: 'FP' for finished goods with financial data
4. Limit to 100 results unless asked for more

QUESTION: {question}

Return ONLY the Cypher query:
"""
                
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=800,
                    messages=[{"role": "user", "content": query_prompt}]
                )
                
                query = response.content[0].text.strip()
                
                # Clean up markdown
                if '```' in query:
                    query = query.split('```')[1]
                    if query.startswith('cypher'):
                        query = query[6:]
                    query = query.strip()
                
                if show_query:
                    st.subheader("Generated Query")
                    st.code(query, language="cypher")
                
                # Execute
                st.subheader("Results")
                
                driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                
                with driver.session() as session:
                    result = session.run(query)
                    data = [dict(r) for r in result]
                
                driver.close()
                
                if len(data) == 0:
                    st.info("No results found")
                else:
                    st.success(f"✓ Found {len(data)} results")
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                    
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Download CSV",
                        data=csv,
                        file_name="results.csv",
                        mime="text/csv"
                    )
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

st.markdown("---")
st.markdown("**Production Control Tower - Berlin Pilot** | Built in 2 days | Real Blue Yonder data + Mock financials")
