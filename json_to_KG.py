import json
import glob
import os
from datetime import datetime
from typing import Dict, Any
import hashlib
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
JSON_DIR = os.getenv("JSON_DIR", "./localization_model_metadata_dataset")

def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """Flatten a nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def hash_dict(d: Dict[str, Any], prefix: str = '') -> str:
    """Create a hash for a dictionary with optional prefix."""
    dhash = hashlib.md5()
    if prefix:
        dhash.update(prefix.encode())
    encoded = json.dumps(d, sort_keys=True).encode()
    dhash.update(encoded)
    return dhash.hexdigest()

class ModelKnowledgeGraph:
    def __init__(self, uri: str, user: str, password: str):
        """Initialize Neo4j connection"""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        """Close the Neo4j connection"""
        self.driver.close()

    def cleanup_database(self):
        """Remove all nodes and relationships from the database"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("Database cleaned up")

    def create_constraints(self):
        """Create uniqueness constraints for the nodes"""
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT model_name IF NOT EXISTS FOR (m:Model) REQUIRE m.name IS UNIQUE",
                "CREATE CONSTRAINT dataset_name IF NOT EXISTS FOR (d:Dataset) REQUIRE d.name IS UNIQUE",
                "CREATE CONSTRAINT service_name IF NOT EXISTS FOR (s:Service) REQUIRE s.name IS UNIQUE",
                "CREATE CONSTRAINT device_id IF NOT EXISTS FOR (d:Device) REQUIRE d.id IS UNIQUE",
                "CREATE CONSTRAINT problem_type_name IF NOT EXISTS FOR (p:ProblemType) REQUIRE p.name IS UNIQUE",
                "CREATE CONSTRAINT hyperparameters_id IF NOT EXISTS FOR (h:Hyperparameters) REQUIRE h.id IS UNIQUE"
            ]
            for constraint in constraints:
                session.run(constraint)
            print("Constraints created")

    def verify_data(self):
        """Verify that all nodes and relationships were created correctly"""
        with self.driver.session() as session:
            # Get node counts
            result = session.run('''
                MATCH (m:Model) RETURN 'Models' as type, count(m) as count 
                UNION ALL 
                MATCH (t:ModelTraining) RETURN 'Training Nodes' as type, count(t) as count
                UNION ALL
                MATCH (h:Hyperparameters) RETURN 'Hyperparameters' as type, count(h) as count
                UNION ALL
                MATCH (p:Parameters) RETURN 'Parameters' as type, count(p) as count
                UNION ALL
                MATCH (d:Device) RETURN 'Devices' as type, count(d) as count
                UNION ALL
                MATCH (i:ModelInference) RETURN 'Inference Nodes' as type, count(i) as count
                UNION ALL
                MATCH (a:ModelArchitecture) RETURN 'Architectures' as type, count(a) as count
                UNION ALL
                MATCH (s:Service) RETURN 'Services' as type, count(s) as count
                UNION ALL
                MATCH (d:Dataset) RETURN 'Datasets' as type, count(d) as count
                UNION ALL
                MATCH ()-[r]->() RETURN 'Relationships' as type, count(r) as count
            ''')
            print("\nKnowledge Graph Statistics:")
            print("-" * 40)
            for record in result:
                print(f"{record['type']}: {record['count']}")


    def create_model_graph(self, model_data: Dict[str, Any], model_name: str):
        """Create nodes and relationships from model data"""
        with self.driver.session() as session:
            # Process model metadata
            session.run("""
            MERGE (m:Model {name: $name})
            SET m.version = $version,
                m.dateCreated = date($dateCreated),
                m.size = $size,
                m.author = $author
            """, {
                'name': model_name,
                'version': model_data['version'],
                'dateCreated': model_data['dateCreated'],
                'size': model_data['size'],
                'author': model_data['author']
            })

            # Process dataset
            session.run("""
            MERGE (d:Dataset {name: $dataset_name})
            SET d.size = $dataset_size
            WITH d
            MATCH (m:Model {name: $model_name})
            MERGE (m)-[:TRAINED_ON]->(d)
            """, {
                'dataset_name': model_data['dataset']['name'],
                'dataset_size': model_data['dataset']['size'],
                'model_name': model_name
            })

            # Process service and problem type
            session.run("""
            MERGE (s:Service {name: $service_name})
            SET s.minAccuracy = $minAccuracy,
                s.minLatency = $minLatency
            WITH s
            MATCH (m:Model {name: $model_name})
            MERGE (m)-[:PROVIDES]->(s)
            WITH s
            MERGE (p:ProblemType {name: $problem_name})
            MERGE (s)-[:SOLUTION_FOR]->(p)
            """, {
                'service_name': model_data['service']['name'],
                'minAccuracy': model_data['service'].get('minAccuracy'),
                'minLatency': model_data['service'].get('minLatency'),
                'model_name': model_name,
                'problem_name': model_data['problemType']
            })

            # Process architecture
            session.run("""
            MERGE (a:ModelArchitecture {type: $architecture_type})
            WITH a
            MATCH (m:Model {name: $model_name})
            MERGE (m)-[:UTILIZES]->(a)
            """, {
                'architecture_type': model_data['architecture']['type'],
                'model_name': model_name
            })

            # Process training data
            training_data = model_data['training']
            evaluation_metrics = flatten_dict(training_data['evaluationMetrics'])
            parameters = training_data['parameters']
            hyperparameters = parameters['hyperparameters']
            hyperparameters_id = hash_dict(hyperparameters)
            
            # Create training device with type
            training_device = training_data['device']
            training_device_id = hash_dict(training_device, 'training')

            # Create training node with metrics
            session.run("""
            MATCH (m:Model {name: $model_name})
            MERGE (t:ModelTraining {model: $model_name})
            SET t.energyConsumptionCPU = $energyConsumptionCPU,
                t.energyConsumptionGPU = $energyConsumptionGPU,
                t.carbonFootprint = $carbonFootprint,
                t += $metrics
            MERGE (t)-[:TRAINS_ON]->(m)
            """, {
                'model_name': model_name,
                'energyConsumptionCPU': training_data.get('powerConsumptionCPU'),
                'energyConsumptionGPU': training_data.get('powerConsumptionGPU'),
                'carbonFootprint': training_data.get('carbonFootprint'),
                'metrics': evaluation_metrics
            })

            # Create device node and link to training
            session.run("""
            MERGE (d:Device {id: $device_id})
            SET d.processor = $processor,
                d.cores = $cores,
                d.graphicsCard = $graphicsCard,
                d.memoryCapacity = $memoryCapacity,
                d.type = 'training'
            WITH d
            MATCH (t:ModelTraining {model: $model_name})
            MERGE (t)-[:RUNS_ON]->(d)
            """, {
                'device_id': training_device_id,
                'processor': training_device['CPU'],
                'cores': training_device['numCores'],
                'graphicsCard': training_device.get('GPU'),
                'memoryCapacity': training_device.get('RAM'),
                'model_name': model_name
            })

            # Create parameters and hyperparameters
            session.run("""
            MATCH (t:ModelTraining {model: $model_name})
            MERGE (p:Parameters {model: $model_name})
            SET p.optimizer = $optimizer,
                p.splitType = $splitType
            MERGE (t)-[:CONTAINS]->(p)
            WITH t
            MERGE (h:Hyperparameters {id: $hyperparameters_id})
            SET h += $hyperparameters
            MERGE (t)-[:USES]->(h)
            """, {
                'model_name': model_name,
                'optimizer': parameters.get('optimizer'),
                'splitType': parameters.get('splitType'),
                'hyperparameters_id': hyperparameters_id,
                'hyperparameters': hyperparameters
            })

            # Process inference data
            for inference in model_data.get('inference', []):
                device = inference.get('device', {})
                device_id = hash_dict(device, 'inference')

                session.run("""
                MATCH (m:Model {name: $model_name})
                MERGE (i:ModelInference {
                    model: $model_name
                })
                SET i.energyConsumption = $energy_consumption,
                    i.carbonFootprint = $carbon_footprint,
                    i.latency = $latency,
                    i.flops = $flops,
                    i.batch_size = $batch_size
                MERGE (i)-[:INFERENCE_ON]->(m)
                MERGE (d:Device {id: $device_id})
                SET d.processor = $processor,
                    d.cores = $cores,
                    d.graphicsCard = $graphicsCard,
                    d.memoryCapacity = $memoryCapacity,
                    d.type = 'inference'
                MERGE (i)-[:RUNS_ON]->(d)
                """, {
                    'model_name': model_name,
                    'energy_consumption': inference.get('energy_consumption'),
                    'carbon_footprint': inference.get('carbon_footprint'),
                    'latency': inference.get('latency'),
                    'flops': inference.get('flops'),
                    'batch_size': inference.get('batch_size'),
                    'device_id': device_id,
                    'processor': device.get('CPU'),
                    'cores': device.get('numCores'),
                    'graphicsCard': device.get('GPU'),
                    'memoryCapacity': device.get('RAM')
                })

def process_json_files():
    """Process all JSON files and create knowledge graph"""
    kg = ModelKnowledgeGraph(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

    try:
        # uncomment to cleanup database before inserting new data
        print("Cleaning up database...")
        kg.cleanup_database()
        
        print("Creating constraints...")
        kg.create_constraints()

        print("\nProcessing JSON files...")
        for json_file in glob.glob(f"{JSON_DIR}/**/*.json", recursive=True):
            try:
                with open(json_file, 'r') as f:
                    model_data = json.load(f)
                    model_name = model_data['name']
                    print(f"Processing: {model_name}")
                    kg.create_model_graph(model_data, model_name)
            except Exception as e:
                print(f"Error processing {json_file}: {str(e)}")

        print("\nVerifying data...")
        kg.verify_data()

    finally:
        kg.close()

if __name__ == "__main__":
    process_json_files()
