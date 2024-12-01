import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

"""from numpy import dot
from numpy.linalg import norm"""

from cache import CacheManager #Semantic Cache Logic Manager

load_dotenv()

class RAGHandler:
    def __init__(self):
        self.endpoint = os.getenv('ENDPOINT_URL')
        self.deployment = os.getenv('DEPLOYMENT_NAME')
        self.search_endpoint = os.getenv('SEARCH_ENDPOINT')
        self.search_key = os.getenv('SEARCH_KEY')
        self.search_index = os.getenv('SEARCH_INDEX_NAME')
        self.azure_oai_key = os.getenv('AZURE_OAI_KEY')
        self.embedding_deployment = os.getenv('EMBEDDING_DEPLOYMENT_NAME')

        self.token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default")
        
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.azure_oai_key,
            api_version="2024-05-01-preview",
        )

        # Initialize the CacheManager
        self.cache_manager = CacheManager()

    def generate_embedding(self, text):
        try:
            embedding_response = self.client.embeddings.create(
                    model=self.embedding_deployment,
                    input=[text]
                )
            embedding = embedding_response.data[0].embedding
            print("Embedding Created Successfuly")
            return embedding
        except Exception as e:
            print(f"Could not generate Embedding for {text}: {e}")
            return None
    
    """def cosine_similarity(self, vec1, vec2):
        return dot(vec1, vec2) / (norm(vec1) * norm(vec2))"""
    
    def perform_rag(self, text):
    
        wrong = f"""
            I'm sorry, but I can't provide that information.
            Please contact <a href='https://wa.me/7049969643'>German</a> for more informtion. Thank you!
        """

        prompt = f"""
            You are an AI assistant that helps people find information about FUPRE (Federal University of Petroleum Resources, Effurun). 
            Only provide information contained in the provided document. Answer user questions that might seem vague as long as they relate to FUPRE. 

            If a user asks a question that is irrelevant or out of context, or not in the retrieved documents, respond politely and warmly with the following message: {wrong}
        """

        try:
            # Send request to Azure OpenAI model
            print("...Processing Request...")
            print("Request: " + text + "\n")

            query_embedding = self.generate_embedding(text)

            #Perform Vector Search on the Cache
            result = self.cache_manager.semantic_filter(query_embedding, text)

            if result:
                print(f"found result in cache:")
                return result['content'], result['citations']
            
            else:
                print("...Sending the request to Azure OpenAI endpoint...")
                completion = self.client.chat.completions.create(
                  model=self.deployment,
                  messages= [
                    {
                      "role": "user",
                      "content": text,
                    }],
                  max_tokens=800,
                  temperature=0.7,
                  top_p=0.95,
                  frequency_penalty=0,
                  presence_penalty=0,
                  stop=None,
                  stream=False,
                  extra_body={
                    "data_sources": [{
                        "type": "azure_search",
                        "parameters": {
                          "endpoint": f"{self.search_endpoint}",
                          "index_name": "fuprebot-01-12-24",
                          "semantic_configuration": "default",
                          "query_type": "semantic",
                          "fields_mapping": {},
                          "in_scope": True,
                          "role_information": f"{prompt}",
                          "filter": None,
                          "strictness": 3,
                          "top_n_documents": 5,
                          "authentication": {
                            "type": "api_key",
                            "key": f"{self.search_key}"
                          }
                        }
                      }]
                  }
                )
                response = completion.choices[0].message

                citations = []
                # Store Citations
                for c in response.context["citations"]:
                    citations.append(
                        {"title": c['title'],
                        "url": c['url']}
                    )

                #Check for wrong response
                #failure_embedding = self.generate_embedding(wrong)
                #response_embedding = self.generate_embedding(response.content)

                #similarity = self.cosine_similarity(response_embedding, failure_embedding)
                #print(f"Similarity score for wrong query: {similarity}")

                #if similarity > 0.9:
                if wrong == response.content:
                    print("Record not stored")
                else:
                    # Store the question, response, citation, and embeddings in MongoDB
                    embedding = self.generate_embedding(text + " " + response.content)
                    self.cache_manager.store_record(text, response.content, citations, embedding)

                return response.content, response.context['citations']
        
        except Exception as e:
            print(f"Error in Performing Rag: {e}")
            return None
