from code_parser import validate_and_parse
from error_detector import analyze_code_errors
from ai_suggester import AISuggester

def run_code_review(student_code):
    print("\n--- Starting AI-Driven Code Review ---")
    
   
    parse_result = validate_and_parse(student_code)
    
    if parse_result["status"] == "error":
        print(f"Stop: {parse_result['message']} at line {parse_result.get('line')}")
        return

    
    print("Step 1: Analyzing code structure...")
    analysis = analyze_code_errors(parse_result["tree"])
    

    print("Step 2: Consulting AI for intelligent feedback...")
    suggester = AISuggester()
    ai_report = suggester.get_suggestions(student_code, analysis["suggestions"])
    
 
    print("\n" + "="*30)
    print("FINAL STUDENT REPORT")
    print("="*30)
    print(ai_report)

if __name__ == "__main__":
   
    code_to_review = """
import math
def area(radius):
    pi_val = 3.14  # Defined but not used (Student error)
    return math.pi * radius * radius
"""
    run_code_review(code_to_review)