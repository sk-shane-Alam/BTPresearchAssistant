# Embeddings
# from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.vectorstores import VectorStoreRetriever
from langchain.chains import RetrievalQA
# from langchain.chains import RetrivalQA

from langchain_ollama import ChatOllama



from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
#- Initialize Ollama

data = """
Class 'subheader': Computer Science > Artificial Intelligence    
Class 'title ': EgoPlan-Bench2: A Benchmark for Multimodal Large Language Model Planning in Real-World Scenarios
Class 'authors': Lu Qiu, Yuying Ge, Yi Chen, Yixiao Ge, Ying Shan, Xihui Liu
Class 'arxivdoi': https://doi.org/10.48550/arXiv.2412.04447      
Focus to learn more
Class 'abstract': The advent of Multimodal Large Language Models, leveraging the power of Large Language Models, has recently demonstrated superior multimodal understanding and reasoning abilities, heralding a new era for artificial general intelligence. However, achieving AGI necessitates more than just comprehension and reasoning. A crucial capability required is effective planning in diverse scenarios, which involves making reasonable decisions based on complex environments to solve real-world problems. Despite its importance, the planning abilities of current MLLMs in varied scenarios remain underexplored. In this paper, we introduce EgoPlan-Bench2, a rigorous and comprehensive benchmark designed to assess the planning capabilities of MLLMs across a wide range of real-world scenarios. EgoPlan-Bench2 encompasses everyday tasks spanning 4 major domains and 24 detailed scenarios, closely aligned with human daily life. EgoPlan-Bench2 is constructed through a semi-automatic process utilizing egocentric videos, complemented by manual verification. Grounded in a first-person perspective, it mirrors the way humans approach problem-solving in everyday life. We evaluate 21 competitive MLLMs and provide an in-depth analysis of their limitations, revealing that they face significant challenges in real-world planning. To further improve the planning proficiency of current MLLMs, we propose a training-free approach using multimodal Chain-of-Thought (CoT) prompting through investigating the effectiveness of various multimodal prompts in complex planning. Our approach enhances the performance of GPT-4V by 10.24 on EgoPlan-Bench2 without additional training. Our work not only sheds light on the current limitations of MLLMs in planning, but also provides insights for future enhancements in this critical area. We have made data and code available at this https URL.   
Class 'subjects': Artificial Intelligence (cs.AI); Computer Vision and Pattern Recognition (cs.CV)
[Document(id='7bc4af1a-131f-4d5f-8233-3712f73b2189', metadata={}, page_content="Class 'subheader': Computer Science > Artificial Intelligence\nClass 'title ': EgoPlan-Bench2: A Benchmark for Multimodal Large Language Model Planning in Real-World Scenarios\nClass 'authors': Lu Qiu, Yuying Ge, Yi Chen, Yixiao Ge, Ying Shan, Xihui Liu\nClass 'arxivdoi': https://doi.org/10.48550/arXiv.2412.04447\nFocus to learn more\nClass 'abstract': The advent of Multimodal Large Language Models, leveraging the power of Large Language Models, has recently demonstrated superior multimodal understanding and reasoning abilities, heralding a new era for artificial general intelligence. However, achieving AGI necessitates more than just comprehension and reasoning. A crucial capability required is effective planning in diverse scenarios, which involves making reasonable decisions based on complex environments to solve real-world problems. Despite its importance, the planning abilities of current MLLMs in varied scenarios remain underexplored. In this paper, we introduce EgoPlan-Bench2, a rigorous and comprehensive benchmark designed to assess the planning capabilities of MLLMs across a wide range of real-world scenarios. EgoPlan-Bench2 encompasses everyday tasks spanning 4 major domains and 24 detailed scenarios, closely aligned with human daily life. EgoPlan-Bench2 is constructed through a semi-automatic process utilizing egocentric videos, complemented by manual verification. Grounded in a first-person perspective, it mirrors the way humans approach problem-solving in everyday life. We evaluate 21 competitive MLLMs and provide an in-depth analysis of their limitations, revealing that they face significant challenges in real-world planning. To further improve the planning proficiency of current MLLMs, we proposenhances the performance of GPT-4V by 10.24 on EgoPlan-Bench2 without additional training. Our work not only sheds light on the current limitations of MLLMs in planning, but also provides insights for future enhancements in this critical area. We have made data and code available at this https URL.\nClass 'subjects': Artificial Intelligence (cs.AI); Computer Vision and Pattern Recognition (cs.CV)")]

"""

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=300,
)

docs = text_splitter.split_text(data)

# print(f'Number of Chunks: {len(docs)}')
# print(docs)


embeddings_llama = OllamaEmbeddings(model="llama3.2") 


library = FAISS.from_texts(docs, embedding=embeddings_llama)


retriever = library.as_retriever()


llm = ChatOllama(model="llama3.2")

query = "Can you please proivde doi for article titled:  EgoPlan-Bench2: A Benchmark for Multimodal Large Language Model Planning in Real-World Scenarios"

system_prompt = (
    "You are a helpful AI assistant called samy."
    "Use the given context to answer the question. "
    "If you don't know the answer, say you don't know. "
    "Use three sentence maximum and keep the answer concise. "
    "You were developed by Tenzin, Tatwansh and Praveen who are students at NSUT(Netaji Subhas University of Technology ), which is a college"
    "Context: {context}"
)
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)
question_answer_chain = create_stuff_documents_chain(llm, prompt)
chain = create_retrieval_chain(retriever, question_answer_chain)

result = chain.invoke({"input": query})
print(result['answer'])