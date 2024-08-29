import os
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
#from nltk.corpus import stopwords
#from nltk.tokenize import word_tokenize

load_dotenv()

class CacheManager:
    def __init__(self):
        self.uri = os.getenv('MONGODB_CONNECTIONSTRING')
        self.database_name = os.getenv('MONGODB_DATABASE')
        self.collection_name = os.getenv('MONGODB_COLLECTION')

        # Create a new client and connect to the server
        self.client = MongoClient(self.uri)

        # Database Credentials
        self.database = self.client[self.database_name]
        self.collection = self.database[self.collection_name]

        #Initialiize English Stopwords
        #self.stop_words = set(stopwords.words('english'))

        # Send a ping to confirm a successful connection
        try:
            self.client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(f"Could not ping Database: {e}")

    """def remove_stopwords(self, text):
        word_tokens = word_tokenize(text)
        filtered_text = [w for w in word_tokens if not w.lower() in self.stop_words]
        return filtered_text"""
    
    def semantic_query(self, query_embedding):
        try:
            # Generate embedding for the search query
            # Sample vector search pipeline
            pipeline = [
            {
                "$vectorSearch": {
                        "index": "vector_index",
                        "queryVector": query_embedding,
                        "path": "embedding",
                        "numCandidates": 100,
                        "limit": 5
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "question": 1,
                    "content": 1,
                    "citations": 1,
                    "score": {
                        "$meta": "vectorSearchScore"
                    }
                }
            }
            ]

            # Execute the search
            results = list(self.collection.aggregate(pipeline))

            response = []
            # Print results
            for i in results:
                if i['score'] > 0.95:
                    response.append(i)
                #print(i)
            return response if response else None
        
        except Exception as e:
            print(f"Failed fetching Embedding: {e}")
            return None

    def semantic_filter(self, query_embedding, query_text):
        try:
            queries = self.semantic_query(query_embedding)

            if queries:
                query_keywords = query_text.lower()
                print(f"query Keywords: {query_keywords}")

                filtered_results = []

                for result in queries:
                    response_text = result['question'].lower()
                    print(f"Response Text: {response_text}")
                    # Check if a significant portion of the keywords match
                    match_count = sum(1 for word in query_keywords if word in response_text)
                    if match_count >= len(query_keywords) * 1.0:  # 100% threshold
                        filtered_results.append(result) 
                
                if filtered_results:
                    print(f"Filtered Results: {filtered_results}")
                    return max(filtered_results, key=lambda x: x['score'])
                else:
                    print("No perfect match found in DB")
                    return None
                #return max(queries, key=lambda x: x['score'])
            else:
                print("No semantic Match found in DB")
                return None
            
        except Exception as e:
            print(f"Failed in hybrid search: {e}")
            return None


    def store_record(self, question, response, citations, embedding):
        try:
            record = {
                'question': question,
                'content': response,
                'citations': citations,
                'embedding': embedding
            }
            self.collection.insert_one(record)
            print(f"Record stored in Cache successfully")
        except Exception as e:
            print(f"Failed to store record: {e}")