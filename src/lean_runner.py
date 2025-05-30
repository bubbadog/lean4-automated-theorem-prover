"""
Lean 4 code execution and compilation utilities
Handles running Lean code and capturing output/errors
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

class LeanRunner:
    """Handles execution of Lean 4 code"""
    
    def __init__(self, playground_dir: str = "lean_playground"):
        self.playground_dir = Path(playground_dir)
        self.playground_dir.mkdir(exist_ok=True)
        self.timeout = int(os.getenv('LEAN_TIMEOUT', 60))
    
    def execute_lean_code(self, lean_code: str, filename: str = "TempTest.lean") -> Dict:
        """
        Execute Lean code and return results
        
        Args:
            lean_code: The Lean code to execute
            filename: Name of the temporary file
            
        Returns:
            Dict with 'success', 'output', 'error' fields
        """
        file_path = self.playground_dir / filename
        
        try:
            # Write code to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(lean_code)
            
            # Execute with Lake
            result = subprocess.run(
                ['lake', 'lean', str(file_path)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=Path.cwd()  # Run from project root where lakefile.lean is
            )
            
            success = result.returncode == 0
            output = result.stdout if result.stdout else ""
            error = result.stderr if result.stderr else ""
            
            return {
                'success': success,
                'output': output,
                'error': error,
                'returncode': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': "",
                'error': f"Execution timed out after {self.timeout} seconds",
                'returncode': -1
            }
        except Exception as e:
            return {
                'success': False,
                'output': "",
                'error': f"Execution failed: {str(e)}",
                'returncode': -1
            }
        finally:
            # Clean up temporary file
            if file_path.exists():
                try:
                    file_path.unlink()
                except:
                    pass
    
    def test_implementation_only(self, task_template: str, code: str) -> Dict:
        """
        Test just the implementation (with proof set to 'sorry')
        
        Args:
            task_template: The Lean template with placeholders
            code: The implementation code
            
        Returns:
            Execution result dict
        """
        # Replace placeholders with code and sorry
        test_code = task_template.replace('{{code}}', code)
        test_code = test_code.replace('{{proof}}', 'sorry')
        
        return self.execute_lean_code(test_code, "ImplementationTest.lean")
    
    def test_full_solution(self, task_template: str, code: str, proof: str) -> Dict:
        """
        Test the complete solution (implementation + proof)
        
        Args:
            task_template: The Lean template with placeholders
            code: The implementation code
            proof: The proof code
            
        Returns:
            Execution result dict
        """
        # Replace placeholders with actual code and proof
        full_code = task_template.replace('{{code}}', code)
        full_code = full_code.replace('{{proof}}', proof)
        
        return self.execute_lean_code(full_code, "FullSolutionTest.lean")
    
    def validate_lean_syntax(self, code: str) -> Dict:
        """
        Quick syntax validation for a piece of Lean code
        
        Args:
            code: The Lean code to validate
            
        Returns:
            Validation result dict
        """
        # Create a minimal test file with imports
        test_template = f"""import Mathlib
import Aesop

{code}
"""
        return self.execute_lean_code(test_template, "SyntaxTest.lean")

def execute_lean_code(lean_code: str, filename: str = "TempTest.lean") -> Dict:
    """
    Convenience function for executing Lean code
    Compatible with the interface expected by the testing framework
    """
    runner = LeanRunner()
    return runner.execute_lean_code(lean_code, filename)
