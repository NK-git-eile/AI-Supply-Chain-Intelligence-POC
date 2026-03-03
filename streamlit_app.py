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

# This week dates (March 2-8, 2026 - Calendar week Mon-Sun)
THIS_WEEK = ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']

# KPIs
with driver.session() as session:
    starting = session.run("""
        MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item)
        WHERE sr.start_date IN $week AND i.item_type IN ['FP', 'SFP']
        RETURN sum(sr.quantity * i.asp) AS revenue, count(DISTINCT sr) AS orders
    """, week=THIS_WEEK).single()
    
    must_win = session.run("""
        MATCH (sr:ScheduledReceipt)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c:Customer {must_win: true})
        MATCH (sr)-[:FOR_ITEM]->(i:Item)
        WHERE sr.start_date IN $week AND i.item_type IN ['FP', 'SFP']
        RETURN sum(sr.quantity * i.asp) AS value, count(DISTINCT c) AS customers
    """, week=THIS_WEEK).single()
    
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

# Two columns
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("💬 Ask Questions")
    question = st.text_area("", height=100, placeholder="Which customer orders depend on Line 5 production this week?", label_visibility="collapsed")
    
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
                    max_tokens=1200,
                    messages=[{"role": "user", "content": f"""You are a Neo4j Cypher query expert. Write a query to answer this question.

CRITICAL DATABASE FACTS:
1. Dates are STRINGS in format 'D-MMM-YY' (e.g., '1-Mar-26', '15-Apr-26')
2. NEVER use date() functions - they don't work with string dates
3. Line names must be EXACT matches from the list below
4. "orders" or "work orders" = ScheduledReceipts (production jobs)
5. Include BOTH FP (finished products) and SFP (semi-finished products)
6. ScheduledReceipts don't have a single WO number - identify by item + start_date + quantity

SCHEMA:

Nodes:
- ScheduledReceipt: item (string), site (string), start_date (string), sched_date (string), quantity (float), line (string - production method)
- Resource: line_name (string - physical line), code (string), site (string)
- Item: code (string), item_type (string: 'FP' or 'SFP'), asp (float), margin (float), margin_pct (float), description (string)
- Customer: customer_number (string), must_win (boolean), country (string)
- Inventory: quantity (float), is_quarantine (boolean)

Relationships:
- (ScheduledReceipt)-[:ON_RESOURCE]->(Resource)
- (ScheduledReceipt)-[:FOR_ITEM]->(Item)
- (ScheduledReceipt)-[:FULFILLS]->(CustomerOrder)-[:FOR_CUSTOMER]->(Customer)
- (Inventory)-[:FOR_ITEM]->(Item)

ACTUAL RESOURCE LINE NAMES (physical lines - use exact strings):
- 'TFS 80/2 (Linie 5 NEU)'
- 'LINIE 9'
- 'Linie 11 EDO-Konfektion. II'
- 'Linie 6 EDO-Konfektion. I'
- 'BOSCH 1 (Linie 1)'
- 'ROMMELAG BOTTELPACK III'
- 'ROMMELAG BOTTELPACK IV'
- 'TFS 20 (Linie 4)'
- 'AGGREGATIONSSTATION 1'

THIS WEEK DATES (March 2-8, 2026 - Calendar week Mon-Sun):
['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']

WORK ORDER IDENTIFICATION:
- Always return these fields to identify a work order: sr.item, sr.start_date, sr.quantity
- Optionally include: sr.sched_date, sr.site, i.description, i.item_type
- Do NOT expand to customer orders unless specifically asked
- One ScheduledReceipt can fulfill multiple CustomerOrders - don't join unless needed

EXAMPLE QUERIES:

Question: "List work orders starting on Line 5 this week"
Query:
MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {{line_name: 'TFS 80/2 (Linie 5 NEU)'}})
MATCH (sr)-[:FOR_ITEM]->(i:Item)
WHERE sr.start_date IN ['2-Mar-26', '3-Mar-26', '4-Mar-26', '5-Mar-26', '6-Mar-26', '7-Mar-26', '8-Mar-26']
RETURN sr.item AS item,
       i.description AS product_name,
       i.item_type AS type,
       sr.start_date AS start_date,
       sr.sched_date AS completion_date,
       sr.quantity AS quantity
ORDER BY sr.start_date
LIMIT 100

Question: "Which work orders have no available inventory?"
Query:
MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item)
WHERE i.item_type IN ['FP', 'SFP']
OPTIONAL MATCH (inv:Inventory)-[:FOR_ITEM]->(i)
WHERE NOT inv.is_quarantine
WITH sr, i, sum(COALESCE(inv.quantity, 0)) AS available_inventory
WHERE available_inventory = 0
RETURN sr.item AS item,
       i.description AS product_name,
       i.item_type AS type,
       sr.start_date AS start_date,
       sr.quantity AS quantity,
       available_inventory
ORDER BY sr.start_date
LIMIT 100

Question: "Which lines make high-margin products?"
Query:
MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource)
MATCH (sr)-[:FOR_ITEM]->(i:Item)
WHERE i.margin_pct > 0.40 AND i.item_type IN ['FP', 'SFP']
RETURN r.line_name AS line,
       count(DISTINCT i.code) AS products,
       sum(sr.quantity * i.margin) AS total_margin
ORDER BY total_margin DESC
LIMIT 10

Question: "Show must-win customers"
Query:
MATCH (c:Customer {{must_win: true}})
OPTIONAL MATCH (c)<-[:FOR_CUSTOMER]-(co:CustomerOrder)<-[:FULFILLS]-(sr:ScheduledReceipt)
OPTIONAL MATCH (sr)-[:FOR_ITEM]->(i:Item)
WHERE i.item_type IN ['FP', 'SFP']
RETURN c.customer_number AS customer,
       c.country AS country,
       count(DISTINCT co) AS orders,
       sum(sr.quantity * i.asp) AS revenue
ORDER BY revenue DESC

Question: "What products have available inventory?"
Query:
MATCH (inv:Inventory)-[:FOR_ITEM]->(i:Item)
WHERE NOT inv.is_quarantine AND inv.quantity > 0 AND i.item_type IN ['FP', 'SFP']
RETURN i.code AS product,
       i.description AS name,
       i.item_type AS type,
       sum(inv.quantity) AS available_qty
ORDER BY available_qty DESC
LIMIT 20

NOW ANSWER THIS QUESTION: {question}

RULES:
- Return ONLY the Cypher query
- Use exact line names from Resource list above
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
                
                if show_query:
                    st.code(query, language="cypher")
                
                with driver.session() as session:
                    data = [dict(r) for r in session.run(query)]
                
                if data:
                    # Show the data table
                    st.dataframe(pd.DataFrame(data), use_container_width=True, height=300)
                    
                    # AI interpretation of results
                    with st.spinner("Interpreting results..."):
                        # Prepare data sample for AI (limit to 20 rows to avoid token limits)
                        data_sample = pd.DataFrame(data).head(20).to_dict('records')
                        
                        interpret_response = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=250,
                            messages=[{"role": "user", "content": f"""The user asked: "{question}"

The query returned {len(data)} results.

Sample of the data (first 20 rows):
{pd.DataFrame(data).head(20).to_string()}

Provide a brief, insightful summary answering the user's question. Focus on:
- Key numbers and totals
- Important patterns or insights
- Direct answer to what they asked

Be concise (2-3 sentences maximum). Use natural business language.

Examples:
- "All 15 products starting on Line 5 this week are high-margin (>40%), representing $4.4M in margin value"
- "Line 9 has the highest revenue this week at $45.2M across 28 work orders"
- "Customer orders span 12 countries, with Germany and Spain accounting for 65% of the volume"
- "5 alternative lines can produce these products: LINIE 9, BOSCH 1, and Linie 6"

Summary:"""}]
                        )
                        
                        summary = interpret_response.content[0].text.strip()
                        st.info(f"💡 **Insight:** {summary}")
                    
                else:
                    # Smart interpretation of empty results
                    interpret_response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=150,
                        messages=[{"role": "user", "content": f"""The user asked: "{question}"

The database query returned no results (0 rows).

Provide a clear, direct answer to the user's question based on this empty result.

Be concise and helpful. Use natural language. Examples:
- "No must-win customers are affected by Line 5 this week"
- "All products starting this week have available inventory"
- "No alternative lines found - products are line-specific"
- "Line 5 has no work orders scheduled this week"

Keep it to 1-2 sentences maximum. Be positive when appropriate.

Answer:"""}]
                    )
                    
                    answer = interpret_response.content[0].text.strip()
                    st.success(f"✅ {answer}")
                    
            except Exception as e:
                st.error(f"Error: {e}")

with col_right:
    st.subheader("🚨 Line Downtime Simulator")
    
    with driver.session() as session:
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
        line_data = [(row['line'], row['orders'], row['revenue']) for row in lines_result]
    
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
                            
                            st.info(f"📅 **{this_week['orders']} orders** starting this week (${this_week['revenue']/1e6:.1f}M revenue)")
                            
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
                            st.write(f"Orders: {this_week['orders']}")
                            st.write(f"Revenue: ${this_week['revenue']/1e6:.1f}M")
                            st.write(f"Margin: ${this_week['margin']/1e6:.1f}M")
                        
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

st.caption("Production Control Tower - Berlin Pilot | Real data + Mock financials")
