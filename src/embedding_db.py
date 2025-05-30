"""
Retrieval-Augmented Generation (RAG) system for Lean 4 documentation
Provides semantic search over Lean 4 examples and documentation
"""

import os
import json
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
import openai
from dotenv import load_dotenv

load_dotenv()

class EmbeddingDB:
    """Vector database for storing and searching Lean 4 documentation"""
    
    def __init__(self, documents_dir: str = "documents", db_dir: str = "embedding_db"):
        self.documents_dir = Path(documents_dir)
        self.db_dir = Path(db_dir)
        self.db_dir.mkdir(exist_ok=True)
        
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
        
        self.chunk_size = int(os.getenv('CHUNK_SIZE', 1000))
        self.overlap_size = int(os.getenv('OVERLAP_SIZE', 200))
        
        self.chunks_file = self.db_dir / "chunks.pkl"
        self.embeddings_file = self.db_dir / "embeddings.npy"
        self.metadata_file = self.db_dir / "metadata.json"
        
        # Load existing database or create new one
        self.chunks = []
        self.embeddings = None
        self.metadata = {}
        self._load_or_create_db()
    
    def _load_or_create_db(self):
        """Load existing database or create new one from documents"""
        if (self.chunks_file.exists() and 
            self.embeddings_file.exists() and 
            self.metadata_file.exists()):
            self._load_db()
        else:
            print("Creating new embedding database...")
            self._create_db()
    
    def _load_db(self):
        """Load existing database"""
        try:
            with open(self.chunks_file, 'rb') as f:
                self.chunks = pickle.load(f)
            
            self.embeddings = np.load(self.embeddings_file)
            
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
            
            print(f"Loaded database with {len(self.chunks)} chunks")
        except Exception as e:
            print(f"Error loading database: {e}")
            self._create_db()
    
    def _create_db(self):
        """Create new database from documents directory"""
        # Create documents directory if it doesn't exist
        self.documents_dir.mkdir(exist_ok=True)
        
        # Process documents
        documents = self._load_documents()
        if not documents:
            print("No documents found, creating with default Lean 4 content")
            documents = self._create_default_documents()
        
        # Split into chunks
        self.chunks = self._split_documents(documents)
        
        if self.chunks:
            # Generate embeddings
            self.embeddings = self._generate_embeddings(self.chunks)
            
            # Save database
            self._save_db()
            print(f"Created database with {len(self.chunks)} chunks")
        else:
            print("No chunks created - using empty database")
    
    def _load_documents(self) -> List[Dict]:
        """Load all documents from documents directory"""
        documents = []
        
        for file_path in self.documents_dir.glob("*.txt"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Split by <EOC> tag if present
                if '<EOC>' in content:
                    sections = content.split('<EOC>')
                else:
                    sections = [content]
                
                for i, section in enumerate(sections):
                    if section.strip():
                        documents.append({
                            'content': section.strip(),
                            'source': str(file_path),
                            'section': i
                        })
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
        
        return documents
    
    def _create_default_documents(self) -> List[Dict]:
        """Create default Lean 4 documentation"""
        default_docs = [
            {
                'content': """
Lean 4 Basic Tactics:
- `rfl`: reflexivity, proves `a = a`
- `simp`: simplification using simp lemmas
- `norm_num`: normalize numerical expressions
- `ring`: prove ring equations
- `omega`: arithmetic over natural numbers and integers
- `sorry`: placeholder (should not be used in final proofs)

Example:
theorem add_comm (a b : Nat) : a + b = b + a := by
  ring
                """,
                'source': 'default_tactics.txt',
                'section': 0
            },
            {
                'content': """
Lean 4 Function Definitions:
- Use `def` for definitions
- Specify types explicitly
- Use pattern matching with `match`

Example:
def factorial (n : Nat) : Nat :=
  match n with
  | 0 => 1
  | n + 1 => (n + 1) * factorial n

def max (a b : Int) : Int :=
  if a >= b then a else b
                """,
                'source': 'default_functions.txt', 
                'section': 0
            },
            {
                'content': """
Lean 4 Proof Tactics:
- `intro`: introduce hypotheses
- `apply`: apply a theorem
- `exact`: provide exact proof term
- `rw`: rewrite using equation
- `split`: case analysis
- `contradiction`: prove false from contradictory hypotheses
- `unfold`: unfold definitions

Example:
theorem modus_ponens (P Q : Prop) (hpq : P → Q) (hp : P) : Q := by
  apply hpq
  exact hp
                """,
                'source': 'default_proofs.txt',
                'section': 0
            }
        ]
        
        # Save default documents
        for doc in default_docs:
            file_path = self.documents_dir / doc['source']
            with open(file_path, 'w') as f:
                f.write(doc['content'])
        
        return default_docs
    
    def _split_documents(self, documents: List[Dict]) -> List[Dict]:
        """Split documents into chunks"""
        chunks = []
        
        for doc in documents:
            content = doc['content']
            
            # Simple chunking by character count
            for i in range(0, len(content), self.chunk_size - self.overlap_size):
                chunk_content = content[i:i + self.chunk_size]
                
                if chunk_content.strip():
                    chunks.append({
                        'content': chunk_content,
                        'source': doc['source'],
                        'section': doc['section'],
                        'chunk_id': len(chunks)
                    })
        
        return chunks
    
    def _generate_embeddings(self, chunks: List[Dict]) -> np.ndarray:
        """Generate embeddings for chunks"""
        print(f"Generating embeddings for {len(chunks)} chunks...")
        
        embeddings = []
        batch_size = 100
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [chunk['content'] for chunk in batch]
            
            try:
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=texts
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                embeddings.extend(batch_embeddings)
                
                print(f"Processed {min(i + batch_size, len(chunks))}/{len(chunks)} chunks")
                
            except Exception as e:
                print(f"Error generating embeddings for batch {i}: {e}")
                # Add zero embeddings as fallback
                batch_embeddings = [[0.0] * 1536] * len(batch)  # Default embedding size
                embeddings.extend(batch_embeddings)
        
        return np.array(embeddings)
    
    def _save_db(self):
        """Save database to disk"""
        with open(self.chunks_file, 'wb') as f:
            pickle.dump(self.chunks, f)
        
        np.save(self.embeddings_file, self.embeddings)
        
        self.metadata = {
            'num_chunks': len(self.chunks),
            'embedding_model': self.embedding_model,
            'chunk_size': self.chunk_size,
            'overlap_size': self.overlap_size
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def search(self, query: str, k: int = None) -> List[Dict]:
        """Search for relevant chunks"""
        if k is None:
            k = int(os.getenv('MAX_CHUNKS', 10))
        
        if not self.chunks or self.embeddings is None:
            return []
        
        try:
            # Generate query embedding
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=[query]
            )
            query_embedding = np.array(response.data[0].embedding).reshape(1, -1)
            
            # Calculate similarities
            similarities = cosine_similarity(query_embedding, self.embeddings)[0]
            
            # Get top k results
            top_indices = np.argsort(similarities)[-k:][::-1]
            
            results = []
            for idx in top_indices:
                chunk = self.chunks[idx].copy()
                chunk['similarity'] = float(similarities[idx])
                results.append(chunk)
            
            return results
            
        except Exception as e:
            print(f"Error during search: {e}")
            return []
    
    def add_document(self, content: str, source: str = "user_added"):
        """Add a new document to the database"""
        doc = {'content': content, 'source': source, 'section': 0}
        new_chunks = self._split_documents([doc])
        
        if new_chunks:
            new_embeddings = self._generate_embeddings(new_chunks)
            
            # Update database
            self.chunks.extend(new_chunks)
            
            if self.embeddings is not None:
                self.embeddings = np.vstack([self.embeddings, new_embeddings])
            else:
                self.embeddings = new_embeddings
            
            # Save updated database
            self._save_db()
            print(f"Added {len(new_chunks)} new chunks")

def create_rag_database():
    """Initialize and return RAG database"""
    return EmbeddingDB()
