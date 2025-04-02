# RAG Chatbot Using OpenAI + FAISS + LangChain (Enhanced Version)

import pandas as pd
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import os

# ========== CONFIGURATION ==========
OPENAI_API_KEY ="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" # or set manually
CSV_PATH = "knowledgebase2.csv"
INDEX_PATH = "faiss_kb_index"
MODEL_NAME = "gpt-4"  # Or use "gpt-3.5-turbo"

# ========== STEP 1: Load & Format ==========
df = pd.read_csv(CSV_PATH)
df.dropna(subset=["Content"], inplace=True)

# Create structured chunks with rich context
df["document"] = (
    "Page Title: " + df["MainTitle"].fillna("") + "\n" +
    "Section: " + df["SectionTitle"].fillna("") + "\n" +
    "Content: " + df["Content"].fillna("")
)

# ========== STEP 2: Chunking ==========
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
docs = []

for _, row in df.iterrows():
    chunks = splitter.create_documents([row["document"]])
    for chunk in chunks:
        chunk.metadata["source"] = row["URL"]
        docs.append(chunk)

# ========== STEP 3: Embedding & Indexing ==========
embeddings = OpenAIEmbeddings(model="text-embedding-3-small", openai_api_key="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")
db = FAISS.from_documents(docs, embeddings)
db.save_local(INDEX_PATH)

# ========== STEP 4: RAG Chain with Strict Prompt ==========
retriever = db.as_retriever()

prompt_template = PromptTemplate.from_template(
    """
    You are a helpful assistant for UT Dallas' Jindal School. 
    Use ONLY the context below to answer the question. 
    If the answer is n"ot in the context, reply:
    "I'm sorry, I don’t have that information in the current knowledge base."

    Context:
    {context}

    Question:
    {question}
    """
)

def get_bot():
    return RetrievalQA.from_chain_type(
        llm = ChatOpenAI(model=MODEL_NAME, temperature=0, openai_api_key="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"),
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True,
        chain_type_kwargs={"prompt": prompt_template}
    )

# ========== STEP 5: Run Chatbot CLI ==========
if __name__ == "__main__":
    qa_chain = get_bot()
    print("\nChatbot is ready! Ask a question (type 'exit' to quit):")
    while True:
        query = input("\nYou: ")
        if query.lower() in ["exit", "quit"]:
            break
        result = qa_chain.invoke(query)
        print("\nBot:", result['result'])
        print("\nSource(s):", [doc.metadata['source'] for doc in result['source_documents']])