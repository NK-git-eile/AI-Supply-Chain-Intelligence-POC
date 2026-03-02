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
    line_options = [f"{line} — {orders} orders, ${rev/1e6:.1f}M" for line, orders, rev in line_data]
    selected_option = st.selectbox("Select line:", line_options)
    selected_line = selected_option.split(" — ")[0]
    
    # DEBUG
    st.info(f"🔍 Searching for: `{selected_line}` (length: {len(selected_line)})")
    
    if st.button("🔧 Simulate Downtime", type="primary"):
        
        # Downtime duration
        downtime_days = 3
        downtime_end = (current_time + timedelta(days=downtime_days)).strftime('%Y-%m-%d')
        
        st.warning(f"⏱️ Simulating {downtime_days}-day downtime (line returns: {downtime_end})")
        
        with driver.session() as session:
            # Check if line exists
            check = session.run("""
                MATCH (r:Resource {line_name: $line})
                RETURN r.line_name AS found
            """, line=selected_line).single()
            
            if not check:
                st.error(f"❌ Line '{selected_line}' not found!")
            else:
                # Total impact (all work orders)
                total_result = session.run("""
                    MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                    MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                    RETURN count(sr) AS total_orders,
                           sum(sr.quantity * i.asp) AS total_revenue,
                           sum(sr.quantity * i.margin) AS total_margin
                """, line=selected_line).single()
                
                # CRITICAL: Orders shipping within downtime period
                critical_result = session.run("""
                    MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                    MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                    MATCH (sr)-[:FULFILLS]->(co:CustomerOrder)
                    WHERE co.ship_date <= $downtime_end
                    RETURN count(sr) AS critical_orders,
                           sum(sr.quantity * i.asp) AS critical_revenue,
                           sum(sr.quantity * i.margin) AS critical_margin,
                           count(DISTINCT co.customer_number) AS critical_customers
                """, line=selected_line, downtime_end=downtime_end).single()
                
                # CAN WAIT: Orders shipping after downtime
                can_wait_result = session.run("""
                    MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                    MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                    MATCH (sr)-[:FULFILLS]->(co:CustomerOrder)
                    WHERE co.ship_date > $downtime_end
                    RETURN count(sr) AS safe_orders,
                           sum(sr.quantity * i.asp) AS safe_revenue
                """, line=selected_line, downtime_end=downtime_end).single()
                
                if total_result and total_result['total_orders'] > 0:
                    st.subheader(f"📊 {downtime_days}-Day Downtime Impact: {selected_line}")
                    
                    # Total Impact
                    st.markdown("### 🔴 TOTAL IMPACT")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Work Orders Affected", f"{total_result['total_orders']}")
                    c2.metric("Revenue at Risk", f"${total_result['total_revenue']/1e6:.1f}M")
                    c3.metric("Margin at Risk", f"${total_result['total_margin']/1e6:.1f}M")
                    
                    st.markdown("---")
                    
                    # Critical vs Can Wait
                    st.markdown("### ⏰ TIME-SENSITIVE ANALYSIS")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### 🚨 CRITICAL (Ship in 3 days)")
                        critical_orders = critical_result['critical_orders'] if critical_result else 0
                        critical_revenue = critical_result['critical_revenue'] if critical_result else 0
                        critical_margin = critical_result['critical_margin'] if critical_result else 0
                        critical_custs = critical_result['critical_customers'] if critical_result else 0
                        
                        st.metric("Orders", f"{critical_orders}", delta="Must expedite", delta_color="inverse")
                        st.metric("Revenue", f"${critical_revenue/1e6:.1f}M")
                        st.metric("Margin", f"${critical_margin/1e6:.1f}M")
                        st.metric("Customers", f"{critical_custs}")
                        
                        if critical_orders > 0:
                            st.error("⚠️ These orders CANNOT wait - immediate action required")
                    
                    with col2:
                        st.markdown("#### ✅ CAN WAIT (Ship after 3 days)")
                        safe_orders = can_wait_result['safe_orders'] if can_wait_result else 0
                        safe_revenue = can_wait_result['safe_revenue'] if can_wait_result else 0
                        
                        st.metric("Orders", f"{safe_orders}", delta="Can delay", delta_color="normal")
                        st.metric("Revenue", f"${safe_revenue/1e6:.1f}M")
                        
                        if safe_orders > 0:
                            st.success("✓ These orders can be rescheduled after line restart")
                    
                    st.markdown("---")
                    
                    # Must-Win Analysis
                    st.markdown("### 🎯 MUST-WIN CUSTOMER ANALYSIS")
                    
                    mw_critical = session.run("""
                        MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                        MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                        MATCH (sr)-[:FULFILLS]->(co:CustomerOrder)-[:FOR_CUSTOMER]->(c:Customer {must_win: true})
                        WHERE co.ship_date <= $downtime_end
                        RETURN count(DISTINCT c) AS mw_customers,
                               count(sr) AS mw_orders,
                               sum(sr.quantity * i.margin) AS mw_margin
                    """, line=selected_line, downtime_end=downtime_end).single()
                    
                    if mw_critical and mw_critical['mw_customers'] > 0:
                        st.error(f"🔴 **{mw_critical['mw_customers']} MUST-WIN customers** shipping in 3 days!")
                        st.write(f"   Orders: {mw_critical['mw_orders']} | Margin: ${mw_critical['mw_margin']/1e3:.0f}K")
                        st.write("   **ACTION:** Expedite or move to alternative line immediately")
                    else:
                        st.success("✓ No must-win customers shipping in critical period")
                    
                    st.markdown("---")
                    
                    # High-Margin Products in Critical Period
                    st.markdown("### 💎 HIGH-MARGIN PRODUCTS (Shipping in 3 days)")
                    
                    hm_critical = session.run("""
                        MATCH (sr:ScheduledReceipt)-[:ON_RESOURCE]->(r:Resource {line_name: $line})
                        MATCH (sr)-[:FOR_ITEM]->(i:Item {item_type: 'FP'})
                        MATCH (sr)-[:FULFILLS]->(co:CustomerOrder)
                        WHERE i.margin_pct > 0.40 AND co.ship_date <= $downtime_end
                        RETURN i.code AS product,
                               i.description AS name,
                               i.margin_pct AS margin_pct,
                               count(sr) AS orders,
                               sum(sr.quantity * i.margin) AS margin_value
                        ORDER BY margin_value DESC
                        LIMIT 10
                    """, line=selected_line, downtime_end=downtime_end)
                    
                    hm_data = []
                    for row in hm_critical:
                        hm_data.append({
                            'Product': row['product'],
                            'Description': row['name'][:40],
                            'Margin %': f"{row['margin_pct']*100:.1f}%",
                            'Orders': row['orders'],
                            'Margin Value': f"${row['margin_value']:,.0f}"
                        })
                    
                    if hm_data:
                        st.dataframe(pd.DataFrame(hm_data), use_container_width=True, hide_index=True)
                        st.warning("⚠️ Prioritize these high-margin products for expediting")
                    else:
                        st.info("No high-margin products shipping in critical period")
                    
                    # RECOMMENDATIONS
                    st.markdown("---")
                    st.markdown("### 💡 RECOMMENDED ACTIONS")
                    
                    if critical_orders > 0:
                        st.markdown("""
                        **IMMEDIATE (Next 24 hours):**
                        1. 🔴 Assess must-win customer orders - expedite or negotiate
                        2. 💎 Prioritize high-margin products (>40% margin)
                        3. 🔧 Investigate alternative lines or overtime options
                        4. 📞 Notify affected customers (especially must-wins)
                        
                        **MEDIUM TERM (24-72 hours):**
                        5. 📋 Reschedule orders shipping after {downtime_end}
                        6. 💰 Calculate expedite costs vs margin protection
                        7. 🏭 Plan line restart sequence by priority
                        
                        **COST-BENEFIT:**
                        - Critical period margin: ${critical_margin/1e6:.1f}M
                        - Typical expedite cost: ~2-5% of order value
                        - Protecting high-margin orders likely worth expediting
                        """)
                    else:
                        st.success("""
                        ✅ **GOOD NEWS:** No orders shipping in critical 3-day period
                        
                        **RECOMMENDED ACTIONS:**
                        1. Use downtime for planned maintenance
                        2. Optimize restart schedule for efficiency
                        3. No immediate customer impact - no expediting needed
                        """)
                
                else:
                    st.warning("No finished goods production on this line")

st.markdown("---")
st.caption("Production Control Tower | Berlin Pilot")
