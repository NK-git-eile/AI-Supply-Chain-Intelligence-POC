import streamlit as st
from neo4j import GraphDatabase
import anthropic
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Production Control Tower", page_icon="🔗", layout="wide")

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
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ Configuration")
    neo4j_uri = st.text_input("Neo4j URI", value=st.secrets.get("NEO4J_URI", ""), type="password")
    neo4j_user = "neo4j"
    neo4j_password = st.text_input("Neo4j Password", type="password", value=st.secrets.get("NEO4J_PASSWORD", ""))
    claude_key = st.text_input("Claude API Key", type="password", value=st.secrets.get("CLAUDE_API_KEY", ""))

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

if not all([neo4j_uri, neo4j_password]):
    st.warning("⚠️ Configure credentials in sidebar")
    st.stop()

driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

st.header("📊 PRODUCTION INTELLIGENCE")

with driver.session() as session:
    week_start = current_time.strftime('%Y-%m-%d')
    week_end = (current_time + timedelta(days=7)).strftime('%Y-%m-%d')
    
    shipping = session.run("""
        MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
        WHERE sr.sched_date >= $start AND sr.sched_date <= $end
        RETURN sum(sr.quantity * i.asp) AS revenue, count(DISTINCT sr) AS orders
    """, start=week_start, end=week_end).single()
    
    must_win = session.run("""
        MATCH (sr:ScheduledReceipt)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c:Customer {must_win: true})
        MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
        WHERE sr.sched_date >= $start AND sr.sched_date <= $end
        RETURN sum(sr.quantity * i.asp) AS value, count(DISTINCT c) AS customers
    """, start=week_start, end=week_end).single()
    
    high_margin = session.run("""
        MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
        WHERE i.margin_pct > 0.40
        RETURN sum(sr.quantity * i.margin) AS margin
    """).single()
    
    active_lines = session.run("""
        MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource)
        MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
        RETURN count(DISTINCT r.line_name) AS total
    """).single()

col1, col2, col3, col4 = st.columns(4)

revenue = shipping['revenue'] if shipping and shipping['revenue'] else 0
orders = shipping['orders'] if shipping and shipping['orders'] else 0
col1.metric("Shipping (7 days)", f"${revenue/1e6:.1f}M", f"{orders} orders")

mw_value = must_win['value'] if must_win and must_win['value'] else 0
mw_custs = must_win['customers'] if must_win and must_win['customers'] else 0
col2.metric("Must-Win Exposure", f"${mw_value/1e6:.1f}M", f"{mw_custs} customers")

hm_margin = high_margin['margin'] if high_margin and high_margin['margin'] else 0
col3.metric("High-Margin (>40%)", f"${hm_margin/1e6:.1f}M")

lines_count = active_lines['total'] if active_lines and active_lines['total'] else 0
col4.metric("Production Lines", f"{lines_count}", "Active")

st.markdown("---")
st.header("🚨 Line Downtime Simulator")

with driver.session() as session:
    lines_result = session.run("""
        MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource)
        MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
        RETURN r.line_name AS line,
               count(sr) AS orders,
               sum(sr.quantity * i.asp) AS revenue
        ORDER BY revenue DESC
        LIMIT 10
    """)
    line_data = [(row['line'], row['orders'], row['revenue']) for row in lines_result]

if line_data:
    line_options = [f"{line} ({orders} orders, ${rev/1e6:.1f}M)" for line, orders, rev in line_data]
    selected_option = st.selectbox("Select line:", line_options)
    selected_line = selected_option.split(" (")[0]
    
    # DEBUG
    st.info(f"🔍 Searching for: `{selected_line}` (length: {len(selected_line)})")
    
    if st.button("🔧 Simulate Downtime", type="primary"):
        with driver.session() as session:
            # First check if line exists
            check = session.run("""
                MATCH (r:Resource {line_name: $line})
                RETURN r.line_name AS found
            """, line=selected_line).single()
            
            if not check:
                st.error(f"❌ Line '{selected_line}' not found in Resources!")
                st.write("Available lines:")
                all_lines = session.run("MATCH (r:Resource) RETURN r.line_name AS line ORDER BY line")
                for row in all_lines:
                    st.write(f"  - `{row['line']}`")
            else:
                st.success(f"✓ Found line: {check['found']}")
                
                result = session.run("""
                    MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                    MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                    RETURN count(sr) AS work_orders,
                           count(DISTINCT i) AS products,
                           sum(sr.quantity * i.asp) AS revenue,
                           sum(sr.quantity * i.margin) AS margin
                """, line=selected_line).single()
                
                if result and result['work_orders'] > 0:
                    st.subheader(f"Impact: {selected_line}")
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Work Orders", result['work_orders'])
                    c2.metric("Products", result['products'])
                    c3.metric("Revenue at Risk", f"${result['revenue']/1e6:.1f}M")
                    c4.metric("Margin at Risk", f"${result['margin']/1e6:.1f}M")
                else:
                    st.warning("No FG production on this line")

st.markdown("---")
st.caption("Production Control Tower | Berlin Pilot")
