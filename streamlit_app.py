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
</style>
""", unsafe_allow_html=True)

# Sidebar
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
            # Shipping this week
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
                RETURN sum(sr.quantity * i.margin) AS margin
            """).single()
            
            # Work orders
            work_orders = session.run("""
                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource)
                MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                RETURN count(sr) AS total
            """).single()
            
            # Active lines
            active_lines = session.run("""
                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource)
                MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                RETURN count(DISTINCT r.line_name) AS total
            """).single()
            
            # Products
            products = session.run("""
                MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                WHERE sr.sched_date >= $start AND sr.sched_date <= $end
                RETURN count(DISTINCT i) AS count
            """, start=week_start, end=week_end).single()
            
            # Volume
            volume = session.run("""
                MATCH (sr:ScheduledReceipt)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                WHERE sr.sched_date >= $start AND sr.sched_date <= $end
                RETURN sum(sr.quantity) AS total
            """, start=week_start, end=week_end).single()
        
        # Display KPIs - Row 1
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
            lines_count = active_lines['total'] if active_lines and active_lines['total'] else 0
            st.metric(
                "Production Lines",
                f"{lines_count}",
                delta="Active"
            )
        
        # Row 2
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            total_orders = work_orders['total'] if work_orders and work_orders['total'] else 0
            st.metric(
                "Work Orders",
                f"{total_orders:,}",
                delta="Scheduled"
            )
        
        with col6:
            prod_count = products['count'] if products and products['count'] else 0
            st.metric(
                "Products",
                f"{prod_count}",
                delta="Unique SKUs"
            )
        
        with col7:
            vol = volume['total'] if volume and volume['total'] else 0
            st.metric(
                "Order Volume",
                f"{vol:,.0f}" if vol > 0 else "0",
                delta="units"
            )
        
        with col8:
            st.metric(
                "Data Status",
                "✓ Live",
                delta="Mock $"
            )
        
        st.markdown("---")
        
      st.markdown("---")
        
        # LINE DOWNTIME SIMULATOR
        st.header("🚨 Line Downtime Impact Simulator")
        
        try:
            with driver.session() as session:
                lines_result = session.run("""
                    MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource)
                    MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                    RETURN r.line_name AS line,
                           count(sr) AS work_orders,
                           sum(sr.quantity * i.asp) AS revenue
                    ORDER BY revenue DESC
                    LIMIT 10
                """)
                
                line_data = [(row['line'], row['work_orders'], row['revenue']) for row in lines_result]
            
            if line_data:
                line_options = [f"{line} ({orders} orders, ${rev/1e6:.1f}M)" 
                               for line, orders, rev in line_data]
                
                selected_line_option = st.selectbox(
                    "Select production line to simulate downtime:",
                    line_options
                )
                
                selected_line = selected_line_option.split(" (")[0].strip()
                
                if st.button("🔧 Simulate Line Downtime", type="primary"):
                    with st.spinner(f"Analyzing impact of {selected_line} downtime..."):
                        
                        with driver.session() as session:
                            result = session.run("""
                                MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                                MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                                RETURN count(sr) AS work_orders,
                                       count(DISTINCT i) AS products,
                                       sum(sr.quantity) AS total_units,
                                       sum(sr.quantity * i.asp) AS revenue_impact,
                                       sum(sr.quantity * i.margin) AS margin_impact,
                                       r.code AS resource_code
                            """, line=selected_line).single()
                            
                            if result and result['work_orders'] > 0:
                                st.subheader(f"📊 Impact Analysis: {selected_line}")
                                
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    st.metric("Work Orders", f"{result['work_orders']}")
                                with col2:
                                    st.metric("Products", f"{result['products']}")
                                with col3:
                                    st.metric("Revenue at Risk", f"${result['revenue_impact']/1e6:.1f}M")
                                with col4:
                                    st.metric("Margin at Risk", f"${result['margin_impact']/1e6:.1f}M")
                                
                                # Customer impact
                                customer_result = session.run("""
                                    MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                                    MATCH (sr)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c)
                                    MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                                    WITH c, 
                                         sum(sr.quantity * i.margin) AS customer_margin,
                                         coalesce(c.must_win, false) AS is_must_win
                                    RETURN count(DISTINCT c) AS total_customers,
                                           sum(CASE WHEN is_must_win THEN 1 ELSE 0 END) AS must_win_customers,
                                           sum(CASE WHEN is_must_win THEN customer_margin ELSE 0 END) AS must_win_margin
                                """, line=selected_line).single()
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.metric("Customers Affected", customer_result['total_customers'])
                                with col2:
                                    if customer_result['must_win_customers'] > 0:
                                        st.metric(
                                            "🔴 Must-Win Customers", 
                                            customer_result['must_win_customers'],
                                            delta=f"${customer_result['must_win_margin']/1e3:.0f}K margin",
                                            delta_color="inverse"
                                        )
                                    else:
                                        st.metric("Must-Win Customers", "0", delta="✓ None affected")
                                
                                # High-margin products
                                st.subheader("💎 High-Margin Products Affected (>40%)")
                                high_margin_result = session.run("""
                                    MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                                    MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                                    WHERE i.margin_pct > 0.40
                                    RETURN i.code AS product,
                                           i.description AS name,
                                           i.margin_pct AS margin_pct,
                                           sum(sr.quantity) AS units,
                                           sum(sr.quantity * i.margin) AS margin_value
                                    ORDER BY margin_value DESC
                                    LIMIT 10
                                """, line=selected_line)
                                
                                hm_data = []
                                for row in high_margin_result:
                                    hm_data.append({
                                        'Product': row['product'],
                                        'Description': row['name'][:50],
                                        'Margin %': f"{row['margin_pct']*100:.1f}%",
                                        'Units': f"{row['units']:,.0f}",
                                        'Margin Value': f"${row['margin_value']:,.0f}"
                                    })
                                
                                if hm_data:
                                    st.dataframe(pd.DataFrame(hm_data), use_container_width=True, hide_index=True)
                                else:
                                    st.info("No high-margin products on this line")
                            
                            else:
                                st.warning("No finished goods production found on this line")
            else:
                st.info("No production lines found with finished goods")
        
        except Exception as e:
            st.error(f"Simulator error: {e}")
        
        st.markdown("---")
        
    except Exception as e:
        st.error(f"Error: {e}")
        import traceback
        st.code(traceback.format_exc())

else:
    st.warning("⚠️ Configure credentials in sidebar")

# Query Interface
st.header("💬 Interactive Query Interface")

st.markdown("Ask questions in plain English. The AI will write and execute database queries.")

with st.expander("📋 Sample Questions"):
    st.markdown("""
    **Financial:** What's the total margin for high-margin products?  
    **Production:** Which lines have the most work orders?  
    **Customers:** Show me must-win customers with orders this week
    """)

question = st.text_area("Your question:", height=100, placeholder="e.g., Which production lines have the highest revenue?")

col1, col2 = st.columns([1, 4])

with col1:
    ask_button = st.button("🔍 Ask AI", type="primary", use_container_width=True)

with col2:
    show_query = st.checkbox("Show query", value=True)

if ask_button:
    if not question.strip():
        st.warning("Please enter a question")
    elif not all([neo4j_uri, neo4j_password, claude_key]):
        st.error("Configure credentials first")
    else:
        with st.spinner("Processing..."):
            try:
                client = anthropic.Anthropic(api_key=claude_key)
                
                query_prompt = f"""Write a Neo4j Cypher query to answer this question.

Schema: ScheduledReceipt-[:ON_RESOURCE]->Resource(line_name), ScheduledReceipt-[:FOR_ITEM]->Item(asp, margin, item_type), ScheduledReceipt-[:FULFILLS]->CustomerOrder-[:FOR_CUSTOMER]->Customer(must_win)

Return ONLY the query. Limit to 100 results.

Question: {question}
"""
                
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=800,
                    messages=[{"role": "user", "content": query_prompt}]
                )
                
                query = response.content[0].text.strip()
                
                if '```' in query:
                    query = query.split('```')[1]
                    if query.startswith('cypher'):
                        query = query[6:]
                    query = query.strip()
                
                if show_query:
                    st.code(query, language="cypher")
                
                driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                
                with driver.session() as session:
                    result = session.run(query)
                    data = [dict(r) for r in result]
                
                if len(data) == 0:
                    st.info("No results")
                else:
                    st.success(f"✓ {len(data)} results")
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                    
                    st.download_button(
                        "📥 Download CSV",
                        df.to_csv(index=False),
                        "results.csv",
                        "text/csv"
                    )
            
            except Exception as e:
                st.error(f"Error: {str(e)}")

st.markdown("---")
st.markdown("**Production Control Tower - Berlin Pilot** | Real Blue Yonder data | Mock financials | Built in 2 days")
