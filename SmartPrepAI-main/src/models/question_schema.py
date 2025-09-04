# We'll be giving two types of question
# to the user either multiple choice or fill in the blanks

from typing import List
from pydantic import BaseModel,Field,validator

class MCQQuestion(BaseModel):
    question: str = Field(description="The question text")
    options: List[str] = Field(description="List of 4 options")
    correct_answer: str = Field(description="The correct answer from the options")
    explanation: str = Field(description="Explanation of why this answer is correct")

    @validator('question' , pre=True)
    def clean_question(cls,v):
        if isinstance(v,dict): ##sometimes the question is passed as a dict with a description key but we want to convert it to a string that's why we check if it's a dict
            return v.get('description' , str(v))
        return str(v)

class FillBlankQuestion(BaseModel):
    question: str = Field(description="The question text with '___' for the blank")
    answer : str = Field(description="The correct word or phrase for the blank")
    explanation: str = Field(description="Explanation of why this answer is correct")

    @validator('question' , pre=True)
    def clean_question(cls,v):
        if isinstance(v,dict):
            return v.get('description' , str(v))
        return str(v)
