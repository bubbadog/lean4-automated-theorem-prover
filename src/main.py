"""
Lean 4 Automated Theorem Prover - Main Workflow

Author: Justin Karbowski 
Course: Advanced Large Language Model Agents, Spring 2025
Date: May 30, 2025

Three-agent system for automated theorem proving with RAG support
"""

import json
import time
from typing import Dict, List, Optional
from pathlib import Path

from agents import PlanningAgent, GenerationAgent, VerificationAgent
from embedding_db import EmbeddingDB
from lean_runner import LeanRunner


class LeanTheoremProver:
    """Main orchestrator for the three-agent theorem proving system"""
    
    def __init__(self):
        # Initialize agents
        self.planning_agent = PlanningAgent()
        self.generation_agent = GenerationAgent()
        self.verification_agent = VerificationAgent()
        
        # Initialize RAG database
        print("Initializing RAG database...")
        self.rag_db = EmbeddingDB()
        
        # Initialize Lean runner
        self.lean_runner = LeanRunner()
        
        # Configuration
        self.max_attempts = 5
        self.max_verification_rounds = 3
    
    def main_workflow(self, problem_description: str, task_template: str) -> Dict[str, str]:
        """
        Main workflow function that processes a theorem proving task
        
        Args:
            problem_description: Natural language description of the task
            task_template: Lean template with {{code}} and {{proof}} placeholders
            
        Returns:
            Dict with 'code' and 'proof' keys containing the solution
        """
        print(f"Starting theorem proving workflow...")
        print(f"Problem: {problem_description[:100]}...")
        
        # Track attempts and context
        context = {
            'description': problem_description,
            'task_template': task_template,
            'attempts': [],
            'successful_implementations': [],
            'error_patterns': set()
        }
        
        for attempt in range(1, self.max_attempts + 1):
            print(f"\n--- Attempt {attempt}/{self.max_attempts} ---")
            
            try:
                result = self._single_attempt(context, attempt)
                if result['success']:
                    print(f"✅ Success on attempt {attempt}!")
                    return {
                        'code': result['code'],
                        'proof': result['proof']
                    }
                else:
                    # Record failed attempt
                    context['attempts'].append({
                        'attempt': attempt,
                        'code': result.get('code', ''),
                        'proof': result.get('proof', ''),
                        'error': result.get('error', ''),
                        'stage': result.get('failed_stage', 'unknown')
                    })
                    
                    # Extract error patterns for better learning
                    if result.get('error'):
                        error_signature = self._extract_error_signature(result['error'])
                        context['error_patterns'].add(error_signature)
                    
            except Exception as e:
                print(f"❌ Attempt {attempt} failed with exception: {e}")
                context['attempts'].append({
                    'attempt': attempt,
                    'error': str(e),
                    'stage': 'exception'
                })
        
        print("❌ All attempts failed. Returning best effort...")
        return self._get_best_effort_result(context)
    
    def _single_attempt(self, context: Dict, attempt_num: int) -> Dict:
        """Execute a single attempt at solving the problem"""
        
        # Stage 1: Planning
        print("🎯 Planning stage...")
        plan_result = self._planning_stage(context, attempt_num)
        if not plan_result['success']:
            return {'success': False, 'failed_stage': 'planning', 'error': plan_result.get('error', '')}
        
        # Stage 2: Generation with RAG
        print("🔨 Generation stage...")
        gen_result = self._generation_stage(context, plan_result['plan'], attempt_num)
        if not gen_result['success']:
            return {'success': False, 'failed_stage': 'generation', 'error': gen_result.get('error', '')}
        
        code = gen_result['code']
        proof = gen_result['proof']
        
        # Stage 3: Verification and refinement
        print("🔍 Verification stage...")
        verification_result = self._verification_stage(context, code, proof, attempt_num)
        
        return verification_result
    
    def _planning_stage(self, context: Dict, attempt_num: int) -> Dict:
        """Execute planning stage with context from previous attempts"""
        
        # Enhance input with previous attempt context
        planning_input = {
            'description': context['description'],
            'task_template': context['task_template'],
            'previous_attempts': context['attempts'][-3:],  # Last 3 attempts
            'error_patterns': list(context['error_patterns'])
        }
        
        # Get relevant RAG context for planning
        rag_query = f"Lean 4 planning strategy {context['description']}"
        rag_context = self._get_rag_context(rag_query, max_chunks=3)
        planning_input['rag_context'] = rag_context
        
        plan_response = self.planning_agent.process(planning_input)
        
        if plan_response.success:
            return {
                'success': True,
                'plan': plan_response.content,
                'plan_metadata': plan_response.metadata
            }
        else:
            return {
                'success': False,
                'error': f"Planning failed: {plan_response.errors}"
            }
    
    def _generation_stage(self, context: Dict, plan: str, attempt_num: int) -> Dict:
        """Execute generation stage with RAG-enhanced context"""
        
        # Get RAG context for generation
        rag_query = f"Lean 4 code proof {context['description']} {plan}"
        rag_context = self._get_rag_context(rag_query, max_chunks=5)
        
        generation_input = {
            'description': context['description'],
            'task_template': context['task_template'],
            'plan': plan,
            'rag_context': rag_context,
            'previous_attempts': context['attempts'][-2:],  # Last 2 attempts
            'attempt_number': attempt_num
        }
        
        gen_response = self.generation_agent.process(generation_input)
        
        if not gen_response.success:
            return {
                'success': False,
                'error': f"Generation failed: {gen_response.errors}"
            }
        
        try:
            result_data = json.loads(gen_response.content) if isinstance(gen_response.content, str) else gen_response.metadata
            
            return {
                'success': True,
                'code': result_data.get('code', ''),
                'proof': result_data.get('proof', ''),
                'explanation': result_data.get('explanation', '')
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to parse generation result: {e}"
            }
    
    def _verification_stage(self, context: Dict, code: str, proof: str, attempt_num: int) -> Dict:
        """Execute verification stage with iterative refinement"""
        
        current_code = code
        current_proof = proof
        
        for verification_round in range(1, self.max_verification_rounds + 1):
            print(f"  🔍 Verification round {verification_round}/{self.max_verification_rounds}")
            
            # Test implementation only first
            impl_result = self.lean_runner.test_implementation_only(
                context['task_template'], current_code
            )
            
            if not impl_result['success']:
                print(f"  ❌ Implementation failed: {impl_result['error'][:100]}...")
                
                # Get verification feedback
                fix_result = self._get_verification_feedback(
                    current_code, current_proof, impl_result['error'], 'implementation'
                )
                
                if fix_result['success'] and fix_result.get('corrected_code'):
                    current_code = fix_result['corrected_code']
                    print(f"  🔧 Applied implementation fix")
                    continue
                else:
                    return {
                        'success': False,
                        'failed_stage': 'implementation_verification',
                        'code': current_code,
                        'proof': current_proof,
                        'error': impl_result['error']
                    }
            
            print(f"  ✅ Implementation verified")
            
            # Test full solution (implementation + proof)
            full_result = self.lean_runner.test_full_solution(
                context['task_template'], current_code, current_proof
            )
            
            if full_result['success']:
                print(f"  ✅ Full solution verified!")
                return {
                    'success': True,
                    'code': current_code,
                    'proof': current_proof
                }
            else:
                print(f"  ❌ Proof failed: {full_result['error'][:100]}...")
                
                # Get verification feedback for proof
                fix_result = self._get_verification_feedback(
                    current_code, current_proof, full_result['error'], 'proof'
                )
                
                if fix_result['success'] and fix_result.get('corrected_proof'):
                    current_proof = fix_result['corrected_proof']
                    print(f"  🔧 Applied proof fix")
                    continue
                elif fix_result['success'] and fix_result.get('corrected_code'):
                    # Sometimes proof errors require code changes
                    current_code = fix_result['corrected_code']
                    current_proof = fix_result.get('corrected_proof', current_proof)
                    print(f"  🔧 Applied combined fix")
                    continue
                else:
                    return {
                        'success': False,
                        'failed_stage': 'proof_verification',
                        'code': current_code,
                        'proof': current_proof,
                        'error': full_result['error']
                    }
        
        # If we've exhausted verification rounds
        return {
            'success': False,
            'failed_stage': 'verification_timeout',
            'code': current_code,
            'proof': current_proof,
            'error': "Exceeded maximum verification rounds"
        }
    
    def _get_verification_feedback(self, code: str, proof: str, error: str, error_type: str) -> Dict:
        """Get debugging feedback from verification agent"""
        
        # Get RAG context for debugging
        rag_query = f"Lean 4 error debugging {error_type} {error[:200]}"
        rag_context = self._get_rag_context(rag_query, max_chunks=3)
        
        verification_input = {
            'code': code,
            'proof': proof,
            'error_output': error,
            'error_type': error_type,
            'rag_context': rag_context
        }
        
        verification_response = self.verification_agent.process(verification_input)
        
        if verification_response.success:
            try:
                result = json.loads(verification_response.content) if isinstance(verification_response.content, str) else verification_response.metadata
                return {
                    'success': True,
                    'corrected_code': result.get('corrected_code'),
                    'corrected_proof': result.get('corrected_proof'),
                    'analysis': result.get('error_analysis', ''),
                    'confidence': result.get('confidence', 0.5)
                }
            except Exception as e:
                return {'success': False, 'error': f"Failed to parse verification feedback: {e}"}
        else:
            return {'success': False, 'error': f"Verification feedback failed: {verification_response.errors}"}
    
    def _get_rag_context(self, query: str, max_chunks: int = 5) -> str:
        """Get relevant context from RAG database"""
        try:
            results = self.rag_db.search(query, k=max_chunks)
            
            if not results:
                return ""
            
            context_parts = []
            for result in results:
                context_parts.append(f"Source: {result['source']}\n{result['content']}\n")
            
            return "\n---\n".join(context_parts)
        except Exception as e:
            print(f"RAG search failed: {e}")
            return ""
    
    def _extract_error_signature(self, error: str) -> str:
        """Extract a signature from error for pattern recognition"""
        # Simple error signature extraction
        lines = error.split('\n')
        signature_parts = []
        
        for line in lines[:3]:  # First 3 lines usually contain key info
            if 'error:' in line.lower():
                signature_parts.append(line.strip())
        
        return ' | '.join(signature_parts)[:200]  # Limit length
    
    def _get_best_effort_result(self, context: Dict) -> Dict[str, str]:
        """Return the best available result when all attempts fail"""
        
        if not context['attempts']:
            return {'code': '-- No implementation generated', 'proof': 'sorry'}
        
        # Find the attempt that got furthest
        best_attempt = None
        best_score = -1
        
        for attempt in context['attempts']:
            score = 0
            if attempt.get('code') and '-- No implementation' not in attempt['code']:
                score += 2
            if attempt.get('proof') and attempt['proof'] != 'sorry':
                score += 1
            if attempt.get('stage') in ['proof_verification', 'verification_timeout']:
                score += 1  # Got past implementation
            
            if score > best_score:
                best_score = score
                best_attempt = attempt
        
        if best_attempt:
            return {
                'code': best_attempt.get('code', '-- Implementation failed'),
                'proof': best_attempt.get('proof', 'sorry')
            }
        else:
            return {'code': '-- All attempts failed', 'proof': 'sorry'}


# Main workflow function for the testing framework
def main_workflow(problem_description: str, task_template: str) -> Dict[str, str]:
    """
    Main entry point for the theorem proving system
    Compatible with the testing framework interface
    
    Args:
        problem_description: Natural language description of the problem
        task_template: Lean template with {{code}} and {{proof}} placeholders
        
    Returns:
        Dict containing 'code' and 'proof' keys
    """
    prover = LeanTheoremProver()
    return prover.main_workflow(problem_description, task_template)
