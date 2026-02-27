import streamlit as st
from neo4j import GraphDatabase
import anthropic
import os

st.set_page_config(page_title="AI Supply Chain Intelligence", page_icon="🔗", layout="wide")

with st.sidebar:
    st.title("⚙️ Configuration")
    neo4j_uri = st.text_input("Neo4j URI", value=os.getenv("NEO4J_URI", ""), type="password")
    neo4j_user = st.text_input("Neo4j User", value="neo4j")
    neo4j_password = st.text_input("Neo4j Password", type="password", value=os.getenv("NEO4J_PASSWORD", ""))
    claude_key = st.text_input("Claude API Key", type="password", value=os.getenv("CLAUDE_API_KEY", ""))
    st.markdown("---")
    st.markdown("### 📊 About")
    st.markdown("AI-powered supply chain intelligence")
    st.markdown("**Built:** 2 days | **Cost:** $50")

st.title("🔗 AI-Enabled Supply Chain Intelligence")
st.markdown("### Real-Time Operational Decision Support")

tab1, tab2 = st.tabs(["🚨 Line Downtime Analysis", "💬 Ask Questions"])

with tab1:
    st.header("Production Line Downtime Scenario")
    
    line_name = st.selectbox("Select Production Line", [
        "02961T-IC_BERLINPL_1_57000_FILLING - PACKING",
        "01743ME-IC_BERLINPL_1_57000_FILLING - PACKING",
        "0211R31D_BERLINPL_1_89000_FILLING"
    ])
    
    if st.button("🔍 Analyze Impact", type="primary"):
        if not all([neo4j_uri, neo4j_password, claude_key]):
            st.error("Please configure credentials in sidebar")
        else:
            with st.spinner("Querying Neo4j..."):
                try:
                    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                    
                    with driver.session() as session:
                        result = session.run("""
                            MATCH (sr:ScheduledReceipt {line: $line})
                            MATCH (sr)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c)
                            RETURN DISTINCT sr.item AS product, sr.quantity AS quantity,
                                   co.order_id AS order_id, c.customer_number AS customer,
                                   c.country AS country, c.must_win AS must_win,
                                   c.otif_current AS otif, c.contract_renewal_days AS renewal_days
                            ORDER BY c.must_win DESC, c.otif_current ASC LIMIT 10
                        """, line=line_name)
                        
                        affected = [dict(r) for r in result]
                    
                    driver.close()
                    
                    if len(affected) == 0:
                        st.warning("No production scheduled on this line")
                    else:
                        st.success(f"✓ Found {len(affected)} affected customers")
                        
                        must_wins = [a for a in affected if a.get('must_win')]
                        if len(must_wins) > 0:
                            st.error(f"⚠️ {len(must_wins)} MUST-WIN customers impacted")
                        
                        st.subheader("📊 Affected Orders")
                        
                        for idx, order in enumerate(affected[:5], 1):
                            with st.expander(f"Order {idx}: Customer {order['customer']} {'🔴 MUST-WIN' if order.get('must_win') else ''}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**Product:** {order['product']}")
                                    st.markdown(f"**Order ID:** {order['order_id']}")
                                    st.markdown(f"**Quantity:** {order['quantity']:,.0f}")
                                with col2:
                                    st.markdown(f"**Customer:** {order['customer']}")
                                    st.markdown(f"**Country:** {order.get('country', 'Unknown')}")
                                    if order.get('must_win'):
                                        st.markdown(f"**OTIF:** {order.get('otif', 0)*100:.0f}%")
                                        st.markdown(f"**Contract Renewal:** {order.get('renewal_days', 'Unknown')} days")
                        
                        st.subheader("🤖 AI Recommendation")
                        
                        with st.spinner("Claude AI analyzing..."):
                            context = f"Line DOWN: {line_name}\n\n{len(must_wins)} MUST-WIN customers affected.\n\n"
                            for order in affected[:3]:
                                context += f"Customer {order['customer']}: "
                                if order.get('must_win'):
                                    context += f"MUST-WIN, OTIF {order.get('otif', 0)*100:.0f}%\n"
                            context += "\nAlternatives: 1hr, 3hr, 4hr changeover. Recommend action."
                            
                            client = anthropic.Anthropic(api_key=claude_key)
                            message = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=1000,
                                messages=[{"role": "user", "content": context}]
                            )
                            
                            st.info(message.content[0].text)
                
                except Exception as e:
                    st.error(f"Error: {e}")

with tab2:
    st.header("💬 Ask Questions About Your Supply Chain")
    st.markdown("**Examples:** Which customers are affected if Line X goes down?")
    
    question = st.text_input("Your question:")
    
    if st.button("🔍 Ask AI", type="primary"):
        if not question:
            st.warning("Please enter a question")
        elif not all([neo4j_uri, neo4j_password, claude_key]):
            st.error("Please configure credentials in sidebar")
        else:
            with st.spinner("Processing..."):
                try:
                    client = anthropic.Anthropic(api_key=claude_key)
                    
                    query_prompt = f"""Write Neo4j Cypher query.
Schema: ScheduledReceipt(item, line, quantity), CustomerOrder(order_id, customer_number), Customer(customer_number, must_win, otif_current)
Relationships: (ScheduledReceipt)-[:FULFILLS]->(CustomerOrder)-[:FOR_CUSTOMER]->(Customer)
Question: {question}
Return ONLY Cypher query."""
                    
                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=500,
                        messages=[{"role": "user", "content": query_prompt}]
                    )
                    
                    query = response.content[0].text.strip().replace('```cypher', '').replace('```', '').strip()
                    st.code(query, language="cypher")
                    
                    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                    with driver.session() as session:
                        result = session.run(query)
                        data = [dict(r) for r in result]
                    driver.close()
                    
                    st.success(f"✓ Found {len(data)} results")
                    if len(data) > 0:
                        st.dataframe(data)
                
                except Exception as e:
                    st.error(f"Error: {e}")

st.markdown("---")
st.markdown("**💰 Cost:** $50 POC vs. BCG $27M | **⚡ Built:** 2 days")
