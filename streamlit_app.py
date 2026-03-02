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

st.header("📊 PRODUCTION INTELLIGENCE - STARTING THIS WEEK")

with driver.session() as session:
    # Production starting this week
    starting = session.run("""
        MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
        WHERE sr.start_date IN ['1-Mar-26', '2-Mar-26', '3-Mar-26', '4-Mar-26', 
                                '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26', '9-Mar-26']
        RETURN sum(sr.quantity * i.asp) AS revenue, count(DISTINCT sr) AS orders
    """).single()
    
    # Must-win exposure
    must_win = session.run("""
        MATCH (sr:ScheduledReceipt)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c:Customer {must_win: true})
        MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
        WHERE sr.start_date IN ['1-Mar-26', '2-Mar-26', '3-Mar-26', '4-Mar-26', 
                                '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26', '9-Mar-26']
        RETURN sum(sr.quantity * i.asp) AS value, count(DISTINCT c) AS customers
    """).single()
    
    # High-margin products
    high_margin = session.run("""
        MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
        WHERE i.margin_pct > 0.40
        RETURN sum(sr.quantity * i.margin) AS margin
    """).single()
    
    # Active lines
    active_lines = session.run("""
        MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource)
        MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
        RETURN count(DISTINCT r.line_name) AS total
    """).single()

col1, col2, col3, col4 = st.columns(4)

revenue = starting['revenue'] if starting and starting['revenue'] else 0
orders = starting['orders'] if starting and starting['orders'] else 0
col1.metric("Starting Production", f"${revenue/1e6:.1f}M", f"{orders} orders")

mw_value = must_win['value'] if must_win and must_win['value'] else 0
mw_custs = must_win['customers'] if must_win and must_win['customers'] else 0
col2.metric("Must-Win Exposure", f"${mw_value/1e6:.1f}M", f"{mw_custs} customers")

hm_margin = high_margin['margin'] if high_margin and high_margin['margin'] else 0
col3.metric("High-Margin (>40%)", f"${hm_margin/1e6:.1f}M")

lines_count = active_lines['total'] if active_lines and active_lines['total'] else 0
col4.metric("Production Lines", f"{lines_count}", "Active")

st.markdown("---")

# QUERY INTERFACE - MOVED UP
st.header("💬 Ask Questions About Your Production")

st.markdown("Ask in plain English - the AI will query your live production data.")

with st.expander("📋 Try these examples"):
    st.markdown("""
    - Which production lines have the most work orders?
    - Show me high-margin products starting production this week
    - What's the total value of must-win customer orders?
    - Which customers have the most orders?
    - Show me products made on TFS 80/2 line
    """)

question = st.text_area("Your question:", height=80, placeholder="e.g., Which lines are making high-margin products?")

col1, col2 = st.columns([1, 4])
with col1:
    ask_button = st.button("🔍 Ask AI", type="primary", use_container_width=True)
with col2:
    show_query = st.checkbox("Show query", value=False)

if ask_button and question and all([neo4j_uri, neo4j_password, claude_key]):
    with st.spinner("Analyzing..."):
        try:
            client = anthropic.Anthropic(api_key=claude_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=800,
                messages=[{"role": "user", "content": f"""Write a Neo4j Cypher query for: {question}

Schema: ScheduledReceipt-[:ON_RESOURCE]->Resource(line_name), [:FOR_ITEM]->Item(asp,margin,margin_pct,item_type), [:FULFILLS]->CustomerOrder-[:FOR_CUSTOMER]->Customer(must_win), Inventory(quantity,is_quarantine)-[:FOR_ITEM]->Item

Return ONLY the query, limit 100."""}]
            )
            
            query = response.content[0].text.strip()
            if '```' in query:
                query = query.split('```')[1].replace('cypher','').strip()
            
            if show_query:
                st.code(query, language="cypher")
            
            with driver.session() as session:
                data = [dict(r) for r in session.run(query)]
            
            if data:
                st.success(f"✓ {len(data)} results")
                st.dataframe(pd.DataFrame(data), use_container_width=True)
            else:
                st.info("No results found")
        except Exception as e:
            st.error(f"Error: {e}")

st.markdown("---")

# LINE DOWNTIME SIMULATOR
st.header("🚨 Line Downtime Impact Simulator")

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
    line_options = [f"{line} — {orders} orders, ${rev/1e6:.1f}M" for line, orders, rev in line_data]
    selected_option = st.selectbox("Select line:", line_options)
    selected_line = selected_option.split(" — ")[0]
    
    if st.button("🔧 Simulate 3-Day Downtime", type="primary"):
        downtime_days = 3
        downtime_end = (current_time + timedelta(days=downtime_days)).strftime('%d-%b-%y')
        
        st.warning(f"⏱️ Simulating {downtime_days}-day downtime")
        
        with driver.session() as session:
            # Total impact
            total = session.run("""
                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                RETURN count(sr) AS orders,
                       sum(sr.quantity * i.asp) AS revenue,
                       sum(sr.quantity * i.margin) AS margin
            """, line=selected_line).single()
            
            if total and total['orders'] > 0:
                st.subheader(f"Impact: {selected_line}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Work Orders", total['orders'])
                c2.metric("Revenue at Risk", f"${total['revenue']/1e6:.1f}M")
                c3.metric("Margin at Risk", f"${total['margin']/1e6:.1f}M")
                
                # Must-win check
                mw = session.run("""
                    MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                    MATCH (sr)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c:Customer {must_win: true})
                    MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                    RETURN count(DISTINCT c) AS customers,
                           sum(sr.quantity * i.margin) AS margin
                """, line=selected_line).single()
                
                if mw and mw['customers'] > 0:
                    st.error(f"🔴 {mw['customers']} must-win customers affected (${mw['margin']/1e3:.0f}K margin)")
                else:
                    st.success("✓ No must-win customers affected")
                
                # High-margin products
                st.write("**High-Margin Products (>40%):**")
                hm = session.run("""
                    MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                    MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                    WHERE i.margin_pct > 0.40
                    RETURN i.code AS product, i.description AS name,
                           i.margin_pct AS margin, sum(sr.quantity * i.margin) AS value
                    ORDER BY value DESC
                    LIMIT 5
                """, line=selected_line)
                
                hm_data = [{'Product': r['product'], 'Name': r['name'][:40],
                           'Margin': f"{r['margin']*100:.0f}%", 'Value': f"${r['value']:,.0f}"} 
                          for r in hm]
                
                if hm_data:
                    st.dataframe(pd.DataFrame(hm_data), hide_index=True)
            else:
                st.warning("No FG production on this line")

st.markdown("---")
st.caption("Production Control Tower - Berlin Pilot | Real Blue Yonder data | Mock financials")
