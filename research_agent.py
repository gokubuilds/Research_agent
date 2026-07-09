import os
from typing import TypedDict
import json 
import re
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from tavily import TavilyClient
from langchain_core.messages import SystemMessage,HumanMessage
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("Set the GROQ_API_KEY environment variable before running this script.")

if not TAVILY_API_KEY:
    raise RuntimeError("Set the TAVILY_API_KEY environment variable before running this script.")



# State
class State(TypedDict):
    topic: str
    status:str
    raw_data:dict
    sources:str
    fact:list
    fetch_attempts: int 
    max_fetch_attempts: int

    structured_data:dict
    summary: str
    categories: dict
    final_report: str
    llm_output: str


def parse_llm_json(raw: str) -> dict:
    clean = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(clean):
        if char != "{":
            continue

        try:
            data, _ = decoder.raw_decode(clean[index:])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue

    return {}


#nodes

#validate_user_topic

def validate_topic(state: State):
    topic = state.get("topic")
    if not topic or not topic.strip():
          return {
              "status": "invalid",
                "final_report": "No topic provided. Please enter a topic."
                }
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0, api_key=GROQ_API_KEY)
    prompt = f"""Is "{topic}" a real, meaningful topic or question a person could research?
    Reply with only one word: YES or NO or VAGUE.
    if topic is empty , return NO.
    if the topic is too vague or too broad, such as "cars", "AI", "technology", or "health", return VAGUE."""
    response = llm.invoke([HumanMessage(content=prompt)])
    result = response.content.strip().lower()
    if result=="vague":
        return {"status": "vague"}
    validity = "yes" in result
    if not validity:
        return {"status": "invalid", "final_report": f"'{topic}' doesn't appear to be a valid topic. Please enter a real subject or question."}
    return {"status": "valid"}

def routing(state: State):
    status=state.get("status")
    if status=="valid":
        return "web_search"
    elif status=="vague":
        return "query_refinement"
    return END


def web_search(state: State):

    attempts=state.get("fetch_attempts",0)+1
    user_input = state["topic"]
    tavily_client=TavilyClient(api_key=TAVILY_API_KEY)
    response=tavily_client.search(user_input)

    return {
        "raw_data": response,
        "fetch_attempts": attempts
    }




def content_classifier(state: State):
    raw_data=state.get("raw_data",{})
    llm=ChatGroq(model="llama-3.1-8b-instant",
    temperature=0.2,api_key=GROQ_API_KEY)
    system_prompt="""You are an expert information extraction assistant.
    Extract relevant facts from the raw search results and return valid JSON only.
    Use this schema:
    {
      "sources": ["https://example.com"],
      "facts": [
        {"text": "fact 1", "confidence": 0.8}
      ],
      "summary": "short summary"
    }
    Rules:
    - Use only information present in the input.
    - Do not invent facts.
    - confidence should be between 0 and 1, how sure you are this fact is correct and clearly supported.
    - If missing, use empty list or empty string.

    use this raw content to categorize 
    raw_data:{raw_data}
    """
    topic=state["topic"]
    user_prompt = f"Topic: {topic}\n\nRaw data:\n{json.dumps(raw_data, ensure_ascii=False)}"
    response=llm.invoke([SystemMessage(content=system_prompt),HumanMessage(content=user_prompt)])
    state["llm_output"]= response.content

    data = parse_llm_json(state["llm_output"])

    return {
        "sources": data.get("sources", []),
        "fact": data.get("facts", []),
        "summary": data.get("summary", ""),
       
        
    }


def check_data(state:State):
    missing=not state.get("fact") or not state.get("sources")
    if missing and state.get("fetch_attempts", 0) < state.get("max_fetch_attempts", 3):
        return "query_refinement"
    return "fact_checker"

def query_refinement(state:State):
    title=state.get("topic")
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.3, api_key=GROQ_API_KEY)
    prompt = f"""The search query "{title}" returned no useful results.
    Rewrite it as a clearer, more specific search query likely to return real information.
    Reply with ONLY the new query text, nothing else."""
    response = llm.invoke([HumanMessage(content=prompt)])

    return {
        "topic": response.content.strip()
        }


# goes through facts with confidence less than 0.5 and tries to search
# for them again to see if we get a better answer
def fact_checker(state: State):
    facts = state.get("fact", [])
    if not facts:
        return {"fact": facts}

    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.2, api_key=GROQ_API_KEY)

    updated_facts = []

    for f in facts:
        # facts might be plain strings from older runs, handle that too
        if isinstance(f, str):
            f = {"text": f, "confidence": 0.5}

        if f.get("confidence", 1) < 0.5:
            # turn the fact into a question to search for
            question_prompt = f"""Turn this fact into a short search question:
            Fact: {f['text']}
            Reply with only the question."""
            question = llm.invoke([HumanMessage(content=question_prompt)]).content.strip()

            search_result = tavily_client.search(question)

            recheck_prompt = f"""Question: {question}
            Search results: {json.dumps(search_result, ensure_ascii=False)}

            Based on the search results, is the fact below correct?
            Fact: {f['text']}

            Reply in this exact format:
            confidence: <number between 0 and 1>
            text: <the corrected or confirmed fact>"""
            recheck = llm.invoke([HumanMessage(content=recheck_prompt)]).content.strip()

            new_confidence = f.get("confidence", 0.5)
            new_text = f["text"]

            for line in recheck.splitlines():
                if line.lower().startswith("confidence:"):
                    try:
                        new_confidence = float(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
                if line.lower().startswith("text:"):
                    new_text = line.split(":", 1)[1].strip()

            if new_confidence > 0.6:
                f["text"] = new_text
                f["confidence"] = new_confidence

        updated_facts.append(f)

    return {"fact": updated_facts}


def content_categorizer(state:State):
    facts=state.get("fact",[])
    if not facts:
        return {
            "categories" : {}
            }
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.2, api_key=GROQ_API_KEY)
    system_prompt = """Group the given facts into 3-5 thematic categories.
    Return valid JSON only: {"categories": {"Category Name": ["exact fact text", ...]}}
    Rules:
    - Use the facts exactly as given, don't reword them.
    - Every fact must appear in exactly one category.
    - Choose category names that describe the theme, not generic labels like "Facts"."""
    fact_texts = [f["text"] if isinstance(f, dict) else f for f in facts]
    user_prompt = json.dumps(fact_texts, ensure_ascii=False)
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])

    data = parse_llm_json(response.content)
    categories = data.get("categories", {})
    
    return {
        "categories": categories
        }

def summarizer(state: State):
    categories = state.get("categories", {})
    if not categories:
        return {
            "final_report": "No information is found based on the given topic . Please retry by giving the topic title clearly. "
            }
    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.3, api_key=GROQ_API_KEY)
    system_prompt = """Write a clean Markdown report from these categorized facts.
    Use a heading for each category, then bullet points for facts under it."""
    user_prompt = json.dumps(categories, ensure_ascii=False)
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
   
    return {
            "final_report": response.content
            }
    

builder = StateGraph(State)

builder.add_node("validate_topic",validate_topic)
builder.add_node("web_search", web_search)
builder.add_node("content_classifier",content_classifier)
builder.add_node("query_refinement", query_refinement)
builder.add_node("fact_checker", fact_checker)
builder.add_node("content_categorizer",content_categorizer)
builder.add_node("summarizer",summarizer)

builder.add_edge(START, "validate_topic")
builder.add_conditional_edges("validate_topic", routing)
builder.add_edge("web_search", "content_classifier")
builder.add_conditional_edges("content_classifier", check_data)
builder.add_edge("query_refinement", "web_search")
builder.add_edge("fact_checker", "content_categorizer")
builder.add_edge("content_categorizer", "summarizer")
builder.add_edge("summarizer", END)

graph = builder.compile()

if __name__ == "__main__":
    result5 = graph.invoke({
        "topic":"bike",
        "fetch_attempts": 0,
        "max_fetch_attempts": 3
    })
    print("TEST 5 - Whitespace-only topic:")

    print(result5["topic"])
