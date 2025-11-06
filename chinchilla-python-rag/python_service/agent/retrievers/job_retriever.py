#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Job Retriever for Elderly Job Matching Agent
Integrates with ChromaDB and Upstage embeddings for RAG
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import chromadb
    from chromadb.config import Settings
    from langchain_upstage import UpstageEmbeddings
    from langchain.schema import Document
except ImportError as e:
    print(f"[ERROR] Install dependencies: pip install chromadb langchain-upstage")
    raise

try:
    from app.config import settings
except Exception:
    settings = None


class ElderlyJobRetriever:
    """
    Retriever for elderly job matching using ChromaDB vector store
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        collection_name: str = "elderly_jobs",
        api_key: Optional[str] = None,
    ):
        """
        Initialize the job retriever

        Args:
            db_path: Path to ChromaDB persistent storage
            collection_name: Name of the collection in ChromaDB
            api_key: Upstage API key (defaults to UPSTAGE_API_KEY env var)
        """
        resolved_db_path = db_path
        if not resolved_db_path:
            if settings and getattr(settings, "chroma_dir", None):
                resolved_db_path = settings.chroma_dir
            else:
                resolved_db_path = "data/vectordb"
        self.db_path = resolved_db_path
        self.collection_name = collection_name

        # Get API key
        self.api_key = (
            api_key or settings.upstage_api_key or os.getenv("UPSTAGE_API_KEY")
        )
        if not self.api_key:
            raise ValueError("UPSTAGE_API_KEY not provided or set in environment")

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(Path(self.db_path).absolute()),
            settings=Settings(anonymized_telemetry=False),
        )

        # Get collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load collection '{collection_name}' from {self.db_path}. "
                f"Please run the data pipeline first. Error: {e}"
            )

        # Initialize embeddings
        self.embeddings = UpstageEmbeddings(
            api_key=self.api_key, model="solar-embedding-1-large"
        )

        print(f"✓ Loaded ElderlyJobRetriever with {self.collection.count()} jobs")

    def retrieve(
        self, query: str, n_results: int = 5, filters: Optional[Dict] = None
    ) -> List[Document]:
        """
        Retrieve relevant job documents for a query

        Args:
            query: User query text
            n_results: Number of results to return
            filters: Metadata filters (e.g., {'region_province': '서울'})

        Returns:
            List of LangChain Document objects
        """
        # Embed query
        query_embedding = self.embeddings.embed_query(query)

        # Retrieve from ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=n_results, where=filters
        )

        # Convert to LangChain Documents
        documents = []
        for doc_text, metadata, doc_id, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["ids"][0],
            results["distances"][0],
        ):
            # Add relevance score to metadata
            # ChromaDB cosine distance is in [0, 2] for normalized vectors
            # distance = 0 → perfect match (score = 1.0)
            # distance = 2 → opposite (score = 0.0)
            # Convert to similarity score in [0, 1]
            metadata["relevance_score"] = max(0.0, 1.0 - (distance / 2.0))
            metadata["doc_id"] = doc_id

            documents.append(Document(page_content=doc_text, metadata=metadata))

        return documents

    def retrieve_by_location(
        self,
        query: str,
        province: Optional[str] = None,
        city: Optional[str] = None,
        n_results: int = 5,
    ) -> List[Document]:
        """
        Retrieve jobs filtered by location

        Args:
            query: User query text
            province: Province filter (e.g., '서울')
            city: City filter (e.g., '용산구')
            n_results: Number of results

        Returns:
            List of LangChain Document objects
        """
        # Build ChromaDB filter with $and operator for multiple conditions
        conditions = []
        if province:
            conditions.append({"region_province": province})
        if city:
            conditions.append({"region_city": city})

        # Use $and operator if multiple conditions
        if len(conditions) > 1:
            filters = {"$and": conditions}
        elif len(conditions) == 1:
            filters = conditions[0]
        else:
            filters = None

        return self.retrieve(query, n_results, filters)

    def retrieve_by_age(
        self, query: str, max_age: int, n_results: int = 5
    ) -> List[Document]:
        """
        Retrieve jobs suitable for given age

        Args:
            query: User query text
            max_age: Maximum age to filter by
            n_results: Number of results

        Returns:
            List of LangChain Document objects
        """
        # Note: ChromaDB filters work as exact match or comparison
        # For age filtering, we want jobs where min_age <= user's age
        # This requires custom filtering after retrieval
        docs = self.retrieve(query, n_results * 2)  # Get more to filter

        # Filter by age requirement
        filtered_docs = [
            doc for doc in docs if doc.metadata.get("min_age", 0) <= max_age
        ]

        return filtered_docs[:n_results]

    def get_job_by_id(self, job_id: str) -> Optional[Document]:
        """
        Retrieve a specific job by its ID

        Args:
            job_id: Job ID to retrieve

        Returns:
            Document if found, None otherwise
        """
        try:
            results = self.collection.get(where={"job_id": job_id})

            if results["documents"]:
                return Document(
                    page_content=results["documents"][0],
                    metadata=results["metadatas"][0],
                )
        except Exception as e:
            print(f"Error retrieving job {job_id}: {e}")

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get retriever statistics

        Returns:
            Dict with statistics about the collection
        """
        total_count = self.collection.count()

        # Sample metadata for analysis
        sample = self.collection.get(limit=min(100, total_count))

        # Count by region
        regions = {}
        for meta in sample["metadatas"]:
            region = meta.get("region_province", "unknown")
            regions[region] = regions.get(region, 0) + 1

        return {
            "total_jobs": total_count,
            "sample_size": len(sample["metadatas"]),
            "regions_sample": regions,
            "collection_name": self.collection_name,
            "db_path": self.db_path,
        }


# Convenience function for agent use
def create_job_retriever(
    db_path: str = "data/vectordb", collection_name: str = "elderly_jobs"
) -> ElderlyJobRetriever:
    """
    Factory function to create job retriever
    """
    return ElderlyJobRetriever(db_path, collection_name)
