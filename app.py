from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from bot import RAGHandler  # Import the class from bot.py

app = FastAPI()
rag_handler = RAGHandler()  # Initialize the RaGHandler instance

class QueryRequest(BaseModel):
    question: str


@app.post("/ask")
async def ask_question(request: QueryRequest):
    try:
        response, citations = rag_handler.perform_rag(request.question)
        return {"response": response, "citations": citations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
