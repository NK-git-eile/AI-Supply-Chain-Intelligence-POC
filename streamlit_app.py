import streamlit as st
from neo4j import GraphDatabase
import anthropic
import os
import pandas as pd

st.set_page_config(page_title="AI Supply Chain Intelligence", page_icon="🔗", layout="wide")

with st.sidebar:
    st.title("⚙️ Configuration")
    neo4j_uri = st.text_input("Neo4j URI", value=os.getenv("NEO4J_URI", ""), type="password")
    neo4j_user = st.text_input("Neo4j User", value="neo4j")
    neo4j_password = st.text_input("Neo4j Password", type="password", value=os.getenv("NEO4J_PASSWORD", ""))
    claude_key = st.text_input("Claude API Key", type="password", value=os.getenv("CLAUDE_API_KEY", ""))
    
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    
    if st.button("Load Stats"):
        if all([neo4j_uri, neo4j_password]):
            try:
                driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                
                with driver.session() as session:
                    sr_count = session.run("MATCH (sr:ScheduledReceipt) RETURN count(sr) AS c").single()['c']
                    co_count = session.run("MATCH (co:CustomerOrder) RETURN count(co) AS c").single()['c']
                    cust_count = session.run("MATCH (c:Customer) RETURN count(c) AS c").single()['c']
                    must_win_count = session.run("MATCH (c:Customer {must_win: true}) RETURN count(c) AS c").single()['c']
                
                driver.close()
                
                st.metric("Scheduled Receipts", f"{sr_count:,}")
                st.metric("Customer Orders", f"{co_count:,}")
                st.metric("Total Customers", cust_count)
                st.metric("Must-Win Customers", must_win_count)
                
            except Exception as e:
                st.error(f"Error: {e}")

st.title("🔗 AI Supply Chain Intelligence")
st.markdown("### Ask Questions About Your Production Plan")

# Main interface - just the query tab
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
    **Production & Capacity:**
    - Show me all production lines
    - Which lines have the most scheduled work?
    - What's scheduled on line [LINE_NAME]?
    - How much total production is scheduled this month?
    
    **Customer Analysis:**
    - Show me all must-win customers
    - Which customers have the most orders?
    - List customers in Germany
    - Show me customers with OTIF below 90%
    
    **Order Analysis:**
    - What orders are shipping next week?
    - Show me orders for customer [CUSTOMER_NUMBER]
    - Which products have the highest volumes?
    - What's the total order volume?
    
    **Risk Analysis:**
    - Which customers are affected if line [LINE_NAME] goes down?
    - Show me must-win customers at risk (low OTIF, upcoming renewal)
    - What's the impact of losing line [LINE_NAME]?
    
    **General Queries:**
    - Show me a sample of the data
    - What's in the database?
    - Give me an overview of scheduled production
    """)

# Question input
question = st.text_area("Your question:", height=100, placeholder="e.g., Show me all must-win customers with their OTIF scores")

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
- ScheduledReceipt: item (product code), site (location), line (production line), quantity, sched_date, start_date
- CustomerOrder: order_id, item, site, customer_number, country, ship_date, quantity, priority
- Customer: customer_number, country, must_win (boolean), otif_current (0.0-1.0), contract_renewal_days, total_volume
- ProductionLine: name, changeover_hours, status

Relationships:
- (ScheduledReceipt)-[:FULFILLS]->(CustomerOrder)-[:FOR_CUSTOMER]->(Customer)

IMPORTANT RULES:
1. Return ONLY the Cypher query, no explanation
2. Use DISTINCT when appropriate to avoid duplicates
3. Limit results to 100 unless asked for more
4. For dates, they are strings in format 'YYYY-MM-DD' or 'MM/DD/YYYY'
5. Product codes and line names are case-sensitive
6. Common line name pattern: product_code + BERLINPL + numbers + process (e.g., '02961T-IC_BERLINPL_1_57000_FILLING - PACKING')

QUESTION: {question}

Return ONLY the Cypher query:
"""
                
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=800,
                    messages=[{"role": "user", "content": query_prompt}]
                )
                
                query = response.content[0].text.strip()
                
                # Clean up markdown formatting
                if '```' in query:
                    query = query.split('```')[1]
                    if query.startswith('cypher'):
                        query = query[6:]
                    query = query.strip()
                
                if show_query:
                    st.subheader("Generated Query")
                    st.code(query, language="cypher")
                
                # Execute query
                st.subheader("Results")
                
                driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                
                with driver.session() as session:
                    result = session.run(query)
                    data = [dict(r) for r in result]
                
                driver.close()
                
                if len(data) == 0:
                    st.info("No results found for this query")
                    st.markdown("**Try:**")
                    st.markdown("- Asking a broader question")
                    st.markdown("- Checking sample questions above")
                    st.markdown("- Asking 'show me a sample of the data' first")
                else:
                    st.success(f"✓ Found {len(data)} results")
                    
                    # Display as dataframe
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                    
                    # Download option
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name="query_results.csv",
                        mime="text/csv"
                    )
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                
                # Try to fix common issues
                if "syntax" in str(e).lower() or "invalid" in str(e).lower():
                    st.warning("The generated query had a syntax error. Trying to fix...")
                    
                    fix_prompt = f"""The query failed with error: {e}

Original query:
{query}

Fix the query and return ONLY the corrected Cypher query:
"""
                    
                    try:
                        fix_response = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=800,
                            messages=[{"role": "user", "content": fix_prompt}]
                        )
                        
                        fixed_query = fix_response.content[0].text.strip()
                        if '```' in fixed_query:
                            fixed_query = fixed_query.split('```')[1]
                            if fixed_query.startswith('cypher'):
                                fixed_query = fixed_query[6:]
                            fixed_query = fixed_query.strip()
                        
                        st.code(fixed_query, language="cypher")
                        st.info("Trying fixed query...")
                        
                        driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                        with driver.session() as session:
                            result = session.run(fixed_query)
                            data = [dict(r) for r in result]
                        driver.close()
                        
                        if len(data) > 0:
                            st.success(f"✓ Fixed! Found {len(data)} results")
                            df = pd.DataFrame(data)
                            st.dataframe(df, use_container_width=True)
                    
                    except Exception as e2:
                        st.error(f"Still failed: {e2}")

st.markdown("---")
st.markdown("**💰 Built in 2 days for $50** | **🎯 Real Blue Yonder data** | **🤖 Powered by Neo4j + Claude AI**")
