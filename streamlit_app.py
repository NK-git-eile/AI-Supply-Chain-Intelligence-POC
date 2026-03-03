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

current_time = datetime.now()
st.markdown(f"""
<div class="main-header">
    <h1>🔗 Production Control Tower - Berlin</h1>
    <p>{current_time.strftime('%B %d, %Y')} | {current_time.strftime('%H:%M')} CET</p>
</div>
""", unsafe_allow_html=True)

if not all([neo4j_uri, neo4j_password]):
    st.warning("⚠️ Configure credentials in sidebar")
    st.stop()

driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

# KPIs - Compact
with driver.session() as session:
    starting = session.run("""
        MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
        WHERE sr.start_date IN ['1-Mar-26', '2-Mar-26', '3-Mar-26', '4-Mar-26', 
                                '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26', '9-Mar-26']
        RETURN sum(sr.quantity * i.asp) AS revenue, count(DISTINCT sr) AS orders
    """).single()
    
    must_win = session.run("""
        MATCH (sr:ScheduledReceipt)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c:Customer {must_win: true})
        MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
        WHERE sr.start_date IN ['1-Mar-26', '2-Mar-26', '3-Mar-26', '4-Mar-26', 
                                '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26', '9-Mar-26']
        RETURN sum(sr.quantity * i.asp) AS value, count(DISTINCT c) AS customers
    """).single()
    
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

revenue = starting['revenue'] if starting and starting['revenue'] else 0
orders = starting['orders'] if starting and starting['orders'] else 0
col1.metric("This Week", f"${revenue/1e6:.1f}M", f"{orders} orders")

mw_value = must_win['value'] if must_win and must_win['value'] else 0
mw_custs = must_win['customers'] if must_win and must_win['customers'] else 0
col2.metric("Must-Win", f"${mw_value/1e6:.1f}M", f"{mw_custs} customers")

hm_margin = high_margin['margin'] if high_margin and high_margin['margin'] else 0
col3.metric("High-Margin", f"${hm_margin/1e6:.1f}M", ">40%")

lines_count = active_lines['total'] if active_lines and active_lines['total'] else 0
col4.metric("Lines", f"{lines_count}", "Active")

# Two columns for query and simulator
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("💬 Ask Questions")
    question = st.text_area("", height=100, placeholder="Which lines make high-margin products?", label_visibility="collapsed")
    
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        ask_button = st.button("🔍 Ask AI", use_container_width=True)
    with col_btn2:
        show_query = st.checkbox("Show query", value=False)
    
    if ask_button and question and all([neo4j_uri, neo4j_password, claude_key]):
        with st.spinner("Analyzing..."):
            try:
                client = anthropic.Anthropic(api_key=claude_key)
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=800,
                    messages=[{"role": "user", "content": f"""Write a Neo4j Cypher query for: {question}

Schema: ScheduledReceipt-[:ON_RESOURCE]->Resource(line_name), [:FOR_ITEM]->Item(asp,margin,margin_pct), [:FULFILLS]->CustomerOrder-[:FOR_CUSTOMER]->Customer(must_win), Inventory-[:FOR_ITEM]->Item

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
                    st.dataframe(pd.DataFrame(data), use_container_width=True, height=300)
                else:
                    st.info("No results")
            except Exception as e:
                st.error(f"Error: {e}")

with col_right:
    st.subheader("🚨 Line Downtime Simulator")
    
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
        selected_option = st.selectbox("", line_options, label_visibility="collapsed")
        selected_line = selected_option.split(" — ")[0]
        
        if st.button("🔧 Simulate 3-Day Downtime", use_container_width=True):
            with st.spinner("Analyzing line impact..."):
                with driver.session() as session:
                    
                    # Analysis Trail
                    with st.expander("🔍 Analysis Trail", expanded=True):
                        st.write("**Step 1:** Identifying work orders...")
                        
                        total = session.run("""
                            MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                            MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                            RETURN count(sr) AS orders,
                                   count(DISTINCT i) AS products,
                                   sum(sr.quantity * i.asp) AS revenue,
                                   sum(sr.quantity * i.margin) AS margin
                        """, line=selected_line).single()
                        
                        if not total or total['orders'] == 0:
                            st.error("❌ No FG production found")
                        else:
                            st.success(f"✓ Found {total['orders']} orders, {total['products']} products")
                            
                            st.write("**Step 2:** Checking this week...")
                            this_week = session.run("""
                                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                                WHERE sr.start_date IN ['1-Mar-26', '2-Mar-26', '3-Mar-26', '4-Mar-26', 
                                                        '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26', '9-Mar-26']
                                RETURN count(sr) AS count
                            """, line=selected_line).single()
                            
                            st.info(f"📅 {this_week['count']} orders starting this week")
                            
                            st.write("**Step 3:** Checking inventory...")
                            inv_check = session.run("""
                                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                                MATCH (sr)-[:FOR_ITEM]->(i:Item)
                                OPTIONAL MATCH (inv:Inventory)-[:FOR_ITEM]->(i)
                                WHERE NOT inv.is_quarantine
                                WITH count(DISTINCT CASE WHEN inv.quantity > 0 THEN i.code END) AS in_stock
                                RETURN in_stock
                            """, line=selected_line).single()
                            
                            if inv_check['in_stock'] > 0:
                                st.success(f"✓ {inv_check['in_stock']} products have stock")
                            else:
                                st.warning("⚠️ Limited inventory")
                            
                            st.write("**Step 4:** Checking must-wins...")
                            mw = session.run("""
                                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                                MATCH (sr)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c:Customer {must_win: true})
                                MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                                RETURN count(DISTINCT c) AS count,
                                       collect(DISTINCT c.customer_number)[0..3] AS ids,
                                       sum(sr.quantity * i.margin) AS margin
                            """, line=selected_line).single()
                            
                            if mw and mw['count'] > 0:
                                st.error(f"🔴 {mw['count']} must-wins: {', '.join(mw['ids'])}")
                            else:
                                st.success("✓ No must-wins affected")
                            
                            st.write("**Step 5:** Analyzing margins...")
                            hm = session.run("""
                                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                                MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                                WHERE i.margin_pct > 0.40
                                RETURN count(DISTINCT i) AS products,
                                       sum(sr.quantity * i.margin) AS margin
                            """, line=selected_line).single()
                            
                            if hm and hm['products'] > 0:
                                st.warning(f"💎 {hm['products']} high-margin products: ${hm['margin']/1e6:.1f}M")
                            
                            st.write("**Step 6:** Searching alternatives...")
                            alt = session.run("""
                                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                                WITH collect(DISTINCT sr.item) AS items
                                UNWIND items AS item
                                MATCH (sr2:ScheduledReceipt {item: item})-[:ON_RESOURCE]->(r2:Resource)
                                WHERE r2.line_name <> $line
                                RETURN count(DISTINCT r2.line_name) AS count
                            """, line=selected_line).single()
                            
                            if alt and alt['count'] > 0:
                                st.success(f"✓ {alt['count']} alternative lines found")
                            else:
                                st.error("❌ No alternatives - line-specific")
                    
                    # Summary
                    st.markdown("**Impact Summary:**")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Orders", total['orders'])
                    c2.metric("Revenue", f"${total['revenue']/1e6:.1f}M")
                    c3.metric("Margin", f"${total['margin']/1e6:.1f}M")
                    
                    # Recommendations
                    st.markdown("**💡 Actions:**")
                    recs = []
                    if mw and mw['count'] > 0:
                        recs.append(f"1. 🔴 Protect must-wins: {', '.join(mw['ids'])}")
                    if hm and hm['products'] > 0:
                        recs.append(f"2. 💎 Prioritize high-margin (${hm['margin']/1e6:.1f}M)")
                    if inv_check['in_stock'] > 0:
                        recs.append(f"3. ✅ Ship {inv_check['in_stock']} from stock")
                    if alt and alt['count'] > 0:
                        recs.append(f"4. 🔧 Consider {alt['count']} alternative lines")
                    else:
                        recs.append("4. ⚠️ Must repair - no alternatives")
                    
                    for rec in recs:
                        st.write(rec)            
            c1, c2, c3 = st.columns(3)
            c1.metric("Work Orders", f"{total['orders']}")
            c2.metric("Revenue at Risk", f"${total['revenue']/1e6:.1f}M")
            c3.metric("Margin at Risk", f"${total['margin']/1e6:.1f}M")
            
            # RECOMMENDATIONS
            st.markdown("### 💡 Recommended Actions")
            
            recommendations = []
            
            if mw and mw['mw_customers'] > 0:
                recommendations.append(f"🔴 **URGENT:** Protect must-win customers ({', '.join(mw['mw_list'])})")
            
            if hm and hm['hm_products'] > 0:
                recommendations.append(f"💎 **HIGH PRIORITY:** Focus on high-margin products (${hm['hm_margin']/1e6:.1f}M at stake)")
            
            if inventory_check and inventory_check['products_in_stock'] > 0:
                recommendations.append(f"✅ **QUICK WIN:** Ship {inventory_check['products_in_stock']} products from available stock")
            
            if alt_lines and alt_lines['alt_count'] > 0:
                recommendations.append(f"🔧 **OPTION:** Consider moving work to: {', '.join(alt_lines['alt_lines'][:2])}")
            else:
                recommendations.append("⚠️ **CONSTRAINT:** No alternative lines - must repair or delay orders")
            
            if orders_this_week > 0:
                recommendations.append(f"⏰ **TIME SENSITIVE:** {orders_this_week} orders scheduled to start this week")
            
            for i, rec in enumerate(recommendations, 1):
                st.write(f"{i}. {rec}")
            
            # DETAILED DATA
            st.markdown("---")
            st.markdown("### 📋 High-Margin Products Detail")
            
            hm_detail = session.run("""
                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                WHERE i.margin_pct > 0.40
                RETURN i.code AS product, 
                       i.margin_pct AS margin,
                       sum(sr.quantity * i.margin) AS value
                ORDER BY value DESC
                LIMIT 5
            """, line=selected_line)
            
            hm_data = [{'Product': r['product'], 
                       'Margin': f"{r['margin']*100:.0f}%",
                       'Value at Risk': f"${r['value']/1e3:.0f}K"} 
                      for r in hm_detail]
            
            if hm_data:
                st.dataframe(pd.DataFrame(hm_data), hide_index=True, use_container_width=True)
st.caption("Production Control Tower - Berlin Pilot | Real data + Mock financials")
