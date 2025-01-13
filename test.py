from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from langchain_groq import ChatGroq

from langchain.sql_database import SQLDatabase


load_dotenv()

db = SQLDatabase.from_uri('mysql+mysqlconnector://root:root@localhost:3306/dsu')

chat_history=[]
def sql_query_generator(db):
    template="""
    You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database.
    Based on the table schema below, write a SQL query that would answer the user's question. Take the Conversation History into account.

    <SCHEMA>{schema}</SCHEMA>

    Conversation History: {chat_history}

    Write only the SQL query and nothing else. Do not wrap the SQL query in any other text, not even backticks.

    For exmaple:
    Question: what are the scheme_name available?
    SQL Query: SELECT Scheme_Name FROM gov_schemes;
    Question: What are the eligibility to obtain government schemes?
    SQL Query: SELECT Eligibility_Criteria FROM gov_schemes;
    Question: i need attendance percentage , name and roll no of all students from section B?
    SQL Query: SELECT S.name, S.roll_no, S.department, S.semester, S.photo, S.status, S.section,
                (COUNT(CASE WHEN A.attendance_status = 'Present' THEN 1 END) / COUNT(*)) * 100 AS attendance_percentage
                FROM students AS S
                JOIN attendance_tbl AS A ON S.roll_no = A.roll_no
                WHERE S.section = 'B'
                GROUP BY S.name, S.roll_no, S.department, S.semester, S.photo, S.status, S.section;

    Your turn:

    Question; {question}
    SQL Query:
     """
    
    prompt = ChatPromptTemplate.from_template(template)

    llm = ChatGroq(model_name="mixtral-8x7b-32768")

    return(RunnablePassthrough.assign(schema=lambda _: db.get_table_info()) 
           | prompt 
           | llm 
           | StrOutputParser())


def response_generator(user_query:str, db: SQLDatabase, chat_history:list):
    sql_chain  = sql_query_generator(db)

    template = """
    You are a data analyst at a company. You are interacting with a user who is asking you questions about the company's database.
    Based on the table schema below, question, sql query, and sql response, write a natural language response.
    <SCHEMA>{schema}</SCHEMA>

    Conversation History: {chat_history}
    SQL Query: <SQL>{query}</SQL>
    User question: {question}
    SQL Response: {response}
    """

    llm = ChatGroq(model_name='mixtral-8x7b-32768')

    prompt = ChatPromptTemplate.from_template(template)

    chain = (
        RunnablePassthrough.assign(query=sql_chain).assign(
        schema = lambda _: db.get_table_info(),
        response = lambda var: db.run(var['query'])
        ) 
        | prompt
        | llm 
        | StrOutputParser()
   
    )

    return chain.invoke({"question":user_query, "chat_history":chat_history})
        





while True:
    user_query = input('enter query ').strip()
    if user_query.lower()=='exit':
        print ("Exiting, Good bye👋")
        break
    chat_history.append(HumanMessage(content=user_query))

    response = response_generator(user_query,db,chat_history)
    if response:
        chat_history.append(AIMessage(content=response))   
    print("MySQL-RAG:",response)