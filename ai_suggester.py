import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate


load_dotenv()

class AISuggester:
    def __init__(self):
        
        self.model = ChatGroq(model_name="llama-3.1-8b-instant")
        
        
        self.template = PromptTemplate(
            input_variables=["code", "errors"],
            template="""
            You are an expert AI Coding Teacher.
            
            Student's Code:
            {code}
            
            Errors Found by Static Analysis:
            {errors}
            
            Please provide a friendly review report including:
            1. Simple explanation of the errors found.
            2. Suggestions for optimization and readability (PEP8)[cite: 27, 28].
            3. Time and Space complexity analysis for the student's logic.
            4. Encouraging feedback to help them learn[cite: 31, 57].
            """
        )

    def get_suggestions(self, code_string, error_list):
        """Generates intelligent suggestions by learning patterns from data [cite: 53]"""
        formatted_prompt = self.template.format(
            code=code_string, 
            errors=", ".join(error_list) if error_list else "No major structural errors found."
        )
        
        try:
            
            response = self.model.invoke(formatted_prompt)
            return response.content
        except Exception as e:
            return f"Error connecting to AI Tutor: {str(e)}"


if __name__ == "__main__":
    suggester = AISuggester()
    sample_code = "def calc(x): y = 10; return x * 2"
    detected_errors = ["Variable 'y' is defined but never used"]
    
    print("\n--- AI Teacher is reviewing your code... ---")
    report = suggester.get_suggestions(sample_code, detected_errors)
    print(report)