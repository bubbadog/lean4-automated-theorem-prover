"""
Testing framework for the Lean 4 theorem proving agent
Processes tasks and evaluates solutions
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import main_workflow
from lean_runner import execute_lean_code

class TaskProcessor:
    """Processes and evaluates theorem proving tasks"""
    
    def __init__(self, tasks_dir: str = "tasks"):
        self.tasks_dir = Path(tasks_dir)
        self.results = []
    
    def discover_tasks(self) -> List[Path]:
        """Discover all task directories"""
        task_dirs = []
        
        if not self.tasks_dir.exists():
            print(f"Tasks directory {self.tasks_dir} not found")
            return task_dirs
        
        for item in self.tasks_dir.iterdir():
            if item.is_dir() and item.name.startswith('task_id_'):
                task_dirs.append(item)
        
        return sorted(task_dirs)
    
    def load_task(self, task_dir: Path) -> Optional[Dict]:
        """Load a single task from directory"""
        try:
            # Load description
            desc_file = task_dir / "description.txt"
            if not desc_file.exists():
                print(f"Missing description.txt in {task_dir}")
                return None
            
            with open(desc_file, 'r', encoding='utf-8') as f:
                description = f.read().strip()
            
            # Load task template
            task_file = task_dir / "task.lean"
            if not task_file.exists():
                print(f"Missing task.lean in {task_dir}")
                return None
            
            with open(task_file, 'r', encoding='utf-8') as f:
                task_template = f.read()
            
            # Load tests (optional)
            tests_file = task_dir / "tests.lean"
            tests_content = ""
            if tests_file.exists():
                with open(tests_file, 'r', encoding='utf-8') as f:
                    tests_content = f.read()
            
            return {
                'task_id': task_dir.name,
                'description': description,
                'task_template': task_template,
                'tests': tests_content,
                'task_dir': task_dir
            }
            
        except Exception as e:
            print(f"Error loading task {task_dir}: {e}")
            return None
    
    def evaluate_solution(self, task: Dict, solution: Dict) -> Dict:
        """Evaluate a solution for a task"""
        task_id = task['task_id']
        print(f"\n🧪 Evaluating solution for {task_id}")
        
        code = solution.get('code', '')
        proof = solution.get('proof', '')
        
        if not code or not proof:
            return {
                'task_id': task_id,
                'success': False,
                'error': 'Missing code or proof',
                'code_compiles': False,
                'proof_valid': False,
                'score': 0
            }
        
        # Check for trivial solutions
        if 'sorry' in proof.lower():
            return {
                'task_id': task_id,
                'success': False,
                'error': 'Sorry placeholder detected',
                'code_compiles': False,
                'proof_valid': False,
                'score': 0
            }

        # Allow short but valid proofs like 'rfl', 'simp', etc.
        valid_short_proofs = ['rfl', 'simp', 'omega', 'norm_num', 'ring']
        if len(proof.strip()) < 10 and not any(valid_proof in proof.lower() for valid_proof in valid_short_proofs):
            return {
                'task_id': task_id,
                'success': False,
                'error': 'Trivial or placeholder proof detected',
                'code_compiles': False,
                'proof_valid': False,
                'score': 0
            }
        
        try:
            # Test implementation only
            impl_test = self._test_implementation(task['task_template'], code)
            
            if not impl_test['success']:
                return {
                    'task_id': task_id,
                    'success': False,
                    'error': f"Implementation failed: {impl_test['error']}",
                    'code_compiles': False,
                    'proof_valid': False,
                    'score': 0
                }
            
            # Test full solution
            full_test = self._test_full_solution(task['task_template'], code, proof)
            
            success = full_test['success']
            score = 1.0 if success else 0.0
            
            return {
                'task_id': task_id,
                'success': success,
                'error': full_test.get('error', ''),
                'code_compiles': True,
                'proof_valid': success,
                'score': score,
                'execution_output': full_test.get('output', '')
            }
            
        except Exception as e:
            return {
                'task_id': task_id,
                'success': False,
                'error': f"Evaluation failed: {str(e)}",
                'code_compiles': False,
                'proof_valid': False,
                'score': 0
            }
    
    def _test_implementation(self, template: str, code: str) -> Dict:
        """Test just the implementation with proof set to sorry"""
        test_code = template.replace('{{code}}', code)
        test_code = test_code.replace('{{proof}}', 'sorry')
        
        return execute_lean_code(test_code, "ImplementationTest.lean")
    
    def _test_full_solution(self, template: str, code: str, proof: str) -> Dict:
        """Test the complete solution"""
        full_code = template.replace('{{code}}', code)
        full_code = full_code.replace('{{proof}}', proof)
        
        return execute_lean_code(full_code, "FullSolutionTest.lean")
    
    def run_single_task(self, task_id: str) -> Optional[Dict]:
        """Run a single task by ID"""
        task_dir = self.tasks_dir / task_id
        if not task_dir.exists():
            print(f"Task {task_id} not found")
            return None
        
        task = self.load_task(task_dir)
        if not task:
            return None
        
        print(f"\n🚀 Processing task: {task_id}")
        print(f"Description: {task['description'][:100]}...")
        
        try:
            # Run the main workflow
            solution = main_workflow(task['description'], task['task_template'])
            
            # Evaluate the solution
            result = self.evaluate_solution(task, solution)
            result['solution'] = solution
            
            self.results.append(result)
            return result
            
        except Exception as e:
            print(f"❌ Task {task_id} failed: {e}")
            result = {
                'task_id': task_id,
                'success': False,
                'error': f"Workflow failed: {str(e)}",
                'score': 0
            }
            self.results.append(result)
            return result
    
    def run_all_tasks(self) -> List[Dict]:
        """Run all discovered tasks"""
        task_dirs = self.discover_tasks()
        
        if not task_dirs:
            print("No tasks found")
            return []
        
        print(f"Found {len(task_dirs)} tasks")
        
        for task_dir in task_dirs:
            self.run_single_task(task_dir.name)
        
        return self.results
    
    def print_summary(self):
        """Print summary of results"""
        if not self.results:
            print("No results to summarize")
            return
        
        total_tasks = len(self.results)
        successful_tasks = sum(1 for r in self.results if r['success'])
        total_score = sum(r['score'] for r in self.results)
        
        print(f"\n{'='*50}")
        print(f"SUMMARY")
        print(f"{'='*50}")
        print(f"Total tasks: {total_tasks}")
        print(f"Successful: {successful_tasks}")
        print(f"Failed: {total_tasks - successful_tasks}")
        print(f"Success rate: {successful_tasks/total_tasks*100:.1f}%")
        print(f"Total score: {total_score:.1f}/{total_tasks}")
        print(f"Average score: {total_score/total_tasks:.3f}")
        
        # Print failed tasks
        failed_tasks = [r for r in self.results if not r['success']]
        if failed_tasks:
            print(f"\nFailed tasks:")
            for result in failed_tasks:
                print(f"  {result['task_id']}: {result['error'][:80]}...")

def main():
    """Main entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Lean theorem proving tests')
    parser.add_argument('--task', type=str, help='Run specific task by ID')
    parser.add_argument('--tasks-dir', type=str, default='tasks', help='Tasks directory')
    
    args = parser.parse_args()
    
    processor = TaskProcessor(args.tasks_dir)
    
    if args.task:
        result = processor.run_single_task(args.task)
        if result:
            print(f"\nResult: {'✅ SUCCESS' if result['success'] else '❌ FAILED'}")
            if not result['success']:
                print(f"Error: {result['error']}")
    else:
        processor.run_all_tasks()
        processor.print_summary()

if __name__ == "__main__":
    main()
