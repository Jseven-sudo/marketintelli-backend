from fastapi import FastAPI

app = FastAPI(title="MarketIntelli Backend")

@app.get("/")
async def root():
    return {"message": "Welcome to MarketIntelli Backend"}
