from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd

app = FastAPI()
pipeline = joblib.load('pipeline.joblib')

# Define a request body model using Pydantic
class Penguin(BaseModel):
    bill_length_mm: float | None = None
    bill_depth_mm: float | None = None
    flipper_length_mm: float | None = None
    body_mass_g: float | None = None
    sex: str | None = None


# Simple POST endpoint
@app.post("/penguins/")
def predict_penguin(penguin: Penguin):
    if not penguin.model_dump(exclude_none=True):
        raise HTTPException(status_code=422, detail="At least one field must be provided")

    
    new_penguin = pd.DataFrame([{
        "bill_length_mm": penguin.bill_length_mm,
        "bill_depth_mm": penguin.bill_depth_mm,
        "flipper_length_mm": penguin.flipper_length_mm,
        "body_mass_g": penguin.body_mass_g,
        "sex": penguin.sex 
    }])
    print(new_penguin)

    
    species = pipeline.predict(new_penguin)[0]

    """Create a new item."""
    return {
        "message": "Species predicted",
        "species": species
    }
