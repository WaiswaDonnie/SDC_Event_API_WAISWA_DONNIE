from fastapi import FastAPI

app = FastAPI(title="Sports Events Api", description="", version="1.0.0")

@app.get("/")
def root():
    return {"message": "Welcome to the Sports Events API!"}

@app.get("/health")
def health_check():
    return {"status": "Ok"}

