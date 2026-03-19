import json
import re

def extract_json(text: str):
    try:
        if not text:
            return None
            
        # Remove markdown ```json ```
        text = re.sub(r"^```json|```$", "", text.strip(), flags=re.MULTILINE).strip()

        # Find first JSON object or array
        start_obj = text.find("{")
        start_arr = text.find("[")
        
        start = start_obj
        if start_obj == -1 and start_arr != -1:
            start = start_arr
        elif start_obj != -1 and start_arr != -1:
            start = min(start_obj, start_arr)
            
        if start == -1:
            return None
            
        # Determine the closing bracket based on opening bracket
        if text[start] == "{":
            end = text.rfind("}") + 1
        else:
            end = text.rfind("]") + 1

        if end == 0:
            return None

        json_str = text[start:end]

        return json.loads(json_str)

    except Exception as e:
        print("JSON PARSE ERROR:", e)
        return None