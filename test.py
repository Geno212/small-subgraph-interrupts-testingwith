import logging

from dotenv import load_dotenv
from pyexpat.errors import messages

_ = load_dotenv()

from langgraph.graph import StateGraph, END, START
from typing import TypedDict, Any
from langgraph.checkpoint.memory import MemorySaver  # Using MemorySaver instead of SqliteSaver
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
import os

# Initialize the model
model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, openai_api_key= "")

G_PROMPT = """You are an assistant for a local brand online shop. \
 Greet the user then ask him to choose a category to select from."""

CE_PROMPT = """You are an assistant for a local brand online shop. \
 Extract and output only the category from the user's prompt. \
 if the user doesnt enter a valid category don't extract anything and return the word empty. \
 Ask the user to enter a category if he hasn't already."""


CHAT_PROMPT = """You are an assistant for a local brand online shop.\
list all products in user chosen category. \
ask the user if he wants to see another category. \
Utilize all the information about the each category's products below as needed: 

------

{content}"""
# Define the State TypedDict
class AgentState(TypedDict):
    message: Any
    greeting: str
    products: str
    categoryPrompt: str
    category: str
    chooseAnotherCat: str
# Subgraph class definition
class Category_Extraction:
    lock = True

    def __init__(self, memory):
        workflow = StateGraph(AgentState)
        workflow.add_node('G', self.G)
        workflow.add_node('CE', self.CE)
        # workflow.add_node('node_3', self.node_3)
        # workflow.add_node('node_4', self.node_4)
       # workflow.add_node('node_5', self.node_5)

        workflow.add_edge(START, 'G')
        workflow.add_edge('G', 'CE')
        # workflow.add_edge('node_2', 'node_3')
        # workflow.add_edge('node_3', 'node_4')
        workflow.add_conditional_edges("CE", self.should_continue,
                                       {"CE":"CE", END: END})
        #workflow.add_edge('node_5', END)

        # Add interrupt points within the subgraph workflow
        self.graph = workflow.compile(
            checkpointer=memory,
            interrupt_before=['CE']  # Interrupt points inside subgraph
        )

    def G(self, state: AgentState):
        # messages = [
        #     SystemMessage(content=G_CE_PROMPT),
        # ]
        print("node G")
        response = "hello, would you be so kind to enter a category :)"
        return {"greeting": response}

    def CE(self, state: AgentState):
        print("node CE")
        messages = [
            SystemMessage(content=CE_PROMPT),
            HumanMessage(content=state.get('categoryPrompt', ''))
        ]
        response = model.invoke(messages)
        print(f"Extracted category: {response.content}")  # Debugging the response

        # Check if the response contains invalid category text
        if any(keyword in response.content.lower() for keyword in ["please enter a category", "empty"]):
            print("Category is invalid, returning empty.")
            return {"category": ""}  # Keep category empty if no valid category is found

        return {"category": response.content}

    def should_continue(self, state):
        if state["category"]:
            return END
        return "CE"
    # def node_2(self, state):
    #     print("node 2 sub")
    #     return {'message': ['hi node 2 sub']}
    #
    # def node_3(self, state):
    #     print("node 3 sub")
    #     return {'message': ['hi node 3 sub']}
    #
    # def node_4(self, state):
    #     print("node 4 sub")
    #     return {'message': ['hi node 4 sub']}
    #
    # def node_5(self, state):
    #     print("node 5 sub")
    #     return {'message': ['hi node 5 sub']}


# Main graph class definition
class Main:
    def __init__(self, memory, Category_Extraction):
        workflow = StateGraph(AgentState)
        workflow.add_node('starting_node', self.node1)
        workflow.add_node('Category_Extraction', Category_Extraction.graph)
        workflow.add_node('chat', self.chat)



        workflow.add_edge(START, 'starting_node')
        workflow.add_edge('starting_node', 'Category_Extraction')
        workflow.add_edge('Category_Extraction', 'chat')
        #workflow.add_edge('node_2', 'node_3')
        workflow.add_conditional_edges("chat", self.should_continue2,
                                       {"Category_Extraction": "Category_Extraction", END: END})

        self.graph = workflow.compile(
            checkpointer=memory,
            interrupt_after=['chat']  # Main graph interrupt point
        )

    def node1(self, state: AgentState):
        print("node 1 main")
        return {'message': ['hi node 1 main']}
    def chat(self, state: AgentState):
        print("node chat")
        content={"shoes": ["sneaker", "boots"],"clothes":["jacket", "pullover"]} # a dictionary of categories with their products
        messages = [
            SystemMessage(content=CHAT_PROMPT.format(content=content)),
            HumanMessage(content=state['category'])
        ]
        response = model.invoke(messages)
        return {"products": response}

    def should_continue2(self, state):
        if "yes" in state['chooseAnotherCat']:
            return "Category_Extraction"

        else:
            return END

def create_main_graph():
    memory = MemorySaver()
    category_extraction = Category_Extraction(memory)
    main_graph = Main(memory, category_extraction)
    return main_graph


# In the run_interrupt_handling function
def run_interrupt_handling():
    memory = MemorySaver()
    category_extraction = Category_Extraction(memory)
    main_graph = Main(memory, category_extraction)

    # Configuration dictionary with required keys
    config = {
        "configurable": {
            "thread_id": "1"  # Example thread_id
        }
    }

    iState = {
        'greeting': '',
        'products': '',
        'categoryPrompt': '',  # Category prompt that we will use in Category Extraction (CE)
        'category': '',  # Will be populated during the CE step
        'chooseAnotherCat': '',  # User response for whether they want to see another category
    }

    # Start the graph and handle interrupts
    i = 1
    while i > 0:
        if i == 1:
            # first time
            for x in main_graph.graph.stream(iState, config=config,subgraphs=True):
                print(x)
        if i == 2:
            # Capture the state after the graph flow
            state = main_graph.graph.get_state(config, subgraphs=True)
           # print(f"here it is{state.tasks[0]}")  # Check what tasks are present

            main_graph.graph.update_state(state.tasks[0].state.config, {"categoryPrompt": "i want shoes"})
            # Update the categoryPrompt and also set category to simulate user selection

           # s['category'] = "shoes"  # Manually set category to match the prompt

           # Continue streaming after the interrupt
            for event in main_graph.graph.stream(None, config=config, subgraphs=True):
                print(event)

            state2 = main_graph.graph.get_state(config).values
            #print(state2)
            # s = snapshot.copy()
            main_graph.graph.update_state(config,{"chooseAnotherCat": "yes please"})
            #print("---\n---\nUpdated state!")
            #print(main_graph.graph.get_state(config).values)
            for event2 in main_graph.graph.stream(None, config=config, subgraphs=True):
                print(event2)

        if i == 3:
            # Capture the state after the graph flow
            state = main_graph.graph.get_state(config, subgraphs=True)
            #print(f"here it is{state.tasks[0]}")  # Check what tasks are present

            main_graph.graph.update_state(state.tasks[0].state.config, {"categoryPrompt": "i want clothes please"})
            # Update the categoryPrompt and also set category to simulate user selection

           # s['category'] = "shoes"  # Manually set category to match the prompt

           # Continue streaming after the interrupt
            for event in main_graph.graph.stream(None, config=config, subgraphs=True):
                print(event)

            state2 = main_graph.graph.get_state(config).values
            #print(state2)
            # s = snapshot.copy()
            main_graph.graph.update_state(config,{"chooseAnotherCat": "no that is it"})
            print("---\n---\nUpdated state!")
            print(main_graph.graph.get_state(config).values)
            for event2 in main_graph.graph.stream(None, config=config, subgraphs=True):
                print(event2)
                if event2 == END:
                    print("Session has ended.")
                    break  # Exit the loop to terminate the session
            state2 = main_graph.graph.get_state(config, subgraphs=True)
            if state2 == END:  # Check if the state has reached the end of the graph
                print("Session has ended.")
                break  # Exit the loop to terminate the session
        i += 1


# Run the interrupt handling code
if __name__ == "__main__":
    run_interrupt_handling()
