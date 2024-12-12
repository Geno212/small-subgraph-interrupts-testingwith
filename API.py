import asyncio
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END

# Import the main workflow classes
from test import create_main_graph, AgentState

# FastAPI Application
app = FastAPI()


# Input models for API
class CategoryPromptInput(BaseModel):
    categoryPrompt: str


class ChooseAnotherCategoryInput(BaseModel):
    chooseAnotherCat: str


# Global variables to manage the graph state
class GraphManager:
    def __init__(self):
        self.current_graph = None
        self.current_config = None
        self.memory = MemorySaver()

    async def start_session(self):
        # Create main graph
        self.current_graph = create_main_graph()

        # Configure session
        self.current_config = {
            "configurable": {
                "thread_id": "1"
            }
        }

        # Initial state
        initial_state: AgentState = {
            'greeting': '',
            'products': '',
            'categoryPrompt': '',
            'category': '',
            'chooseAnotherCat': '',
        }

        # Start the graph
        async for event in self.current_graph.graph.astream(initial_state, config=self.current_config, subgraphs=True):
            print(f"Session Start Event: {event}")

        return {"status": "Session started", "message": "Waiting for category input"}

    async def set_category_prompt(self, categoryPrompt: str):
        if not self.current_graph or not self.current_config:
            raise HTTPException(status_code=400, detail="No active session. Start a session first.")

        # Get current state
        state = self.current_graph.graph.get_state(self.current_config, subgraphs=True)

        # Update state with category prompt
        self.current_graph.graph.update_state(
            state.tasks[0].state.config,
            {"categoryPrompt": categoryPrompt}
        )

        # Continue streaming
        async for event in self.current_graph.graph.astream(None, config=self.current_config, subgraphs=True):
            print(f"Category Prompt Event: {event}")

        return {"status": "Category prompt set", "categoryPrompt": categoryPrompt}

    async def choose_another_category(self, chooseAnotherCat: str):
        if not self.current_graph or not self.current_config:
            raise HTTPException(status_code=400, detail="No active session. Start a session first.")

        # Update state with choose another category
        self.current_graph.graph.update_state(
            self.current_config,
            {"chooseAnotherCat": chooseAnotherCat}
        )

        # Continue streaming
        async for event in self.current_graph.graph.astream(None, config=self.current_config, subgraphs=True):
            print(f"Choose Category Event: {event}")

        return {
            "status": "Session updated",
            "chooseAnotherCat": chooseAnotherCat,
            "message": "Continuing or ending session"
        }

    async def end_session(self):
        if self.current_graph:
            # Potentially add cleanup logic
            self.current_graph = None
            self.current_config = None
        return {"status": "Session ended"}


# Create a singleton graph manager
graph_manager = GraphManager()


@app.post("/start_session")
async def start_session():
    return await graph_manager.start_session()


@app.post("/set_category_prompt")
async def set_category_prompt(input: CategoryPromptInput):
    return await graph_manager.set_category_prompt(input.categoryPrompt)


@app.post("/choose_another_category")
async def choose_another_category(input: ChooseAnotherCategoryInput):
    return await graph_manager.choose_another_category(input.chooseAnotherCat)


@app.post("/end_session")
async def end_session():
    return await graph_manager.end_session()


def run_api_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    # Run the FastAPI server
    run_api_server()