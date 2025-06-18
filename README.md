# MRM3: Machine Readable ML Model Metadata

This project helps manage and analyze information about machine learning models (model metadata) by storing it in a knowledge graph database. When training ML models, we collect important details like how well the model performs, how much energy it uses, what kind of hardware it needs, and what data it was trained on. By organizing all this information in a graph structure, we make it easy to find the right model for specific needs, compare different models, and understand their environmental impact. The project includes schemas on how to collect this metadata in a standard format and store it in a Neo4j graph database, which is a knowledge graph that can then be queried to answer questions about the models. It enables use cases presented below.

## Installation

1. Clone the repository:
2. Install dependencies:
3. Configure environment variables:
```bash
cp .env.template .env
```
Edit `.env` with your Neo4j credentials and desired configuration settings. (See how to deploy a Neo4j instance using Docker below)

The following environment variables can be configured in your `.env` file:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here

# Application Settings
JSON_DIR=./localization_model_metadata_dataset
```

## Usage

1. Run the following command to deploy a Neo4j instance using Docker (optional):

```bash
docker run --name neo4j -p 7474:7474 -p 7687:7687 -d -e NEO4J_AUTH=neo4j/your-password-here neo4j:latest
```

2. Place your ML model metadata JSON files in the configured `JSON_DIR` directory. 
    - (optional) If you don't have any model metadata yet, you can use the example localization model metadata JSON files provided in the `localization_model_metadata_dataset/compressed.zip` file. Extract and proceed to step 4.
3. Ensure your JSON files conform to the schema defined in `json_schema/model_card_schema.json`. You can use the `json_schema/schema_validator.py` script to validate your JSON files.
4. Run the script to insert metadata from JSON files into the Neo4j knowledge graph:
```bash
python json_to_KG.py
```

## Graph Structure

The knowledge graph implements the following structure:

### Node Types

- **Model**: Core node containing model name, version, description, and author information
- **Dataset**: Training data information including name, size, version, and date
- **Service**: Defines the service the model provides (e.g., localization, text generation)
- **ProblemType**: Specifies the ML problem type (regression, classification, etc.)
- **ModelArchitecture**: Details about the model's architecture
- **Device**: Hardware specifications for training/inference
- **ModelTraining**: Training metrics and parameters
- **ModelInference**: Inference performance data
- **Parameters**: Training parameters including optimizer and split type
- **Hyperparameters**: Model hyperparameters such as learning rate, batch size

### Relationships

- **TRAINED_ON**: Connects Model to Dataset
- **PROVIDES**: Links Model to Service
- **UTILIZES**: Associates Model with ModelArchitecture
- **RUNS_ON**: Connects ModelTraining/ModelInference to Device
- **TRAINS_ON**: Links ModelTraining to Model
- **SOLUTION_FOR**: Connects Service to ProblemType
- **CONTAINS**: Links ModelTraining to Parameters
- **USES**: Connects ModelTraining to Hyperparameters
- **INFERENCE_ON**: Links ModelInference to Model

## Ontology Diagram

The following diagram illustrates the ontology of the knowledge graph:

![Ontology Diagram](fig/ontology_diagram.png)


## Use Cases

The ML model metadata knowledge graph enables several key applications, from environmental impact optimization to intelligent model deployment and natural language-based exploration.

### Green Computing Applications
- Intelligent selection of ML models based on energy consumption and carbon footprint metrics through both Neo4j queries and potentially graph neural networks (GNN)
- Analysis of how model architectures and datasets affect carbon footprint
- Workload shifting capabilities to reduce overall environmental impact

### Intelligent ML Model Orchestration
- Comprehensive knowledge of training and inference metrics (latency, computational complexity, carbon footprint, accuracy)
- Possible integration with MLOps systems for optimized training and deployment on distributed infrastructure
- This could enhance performance on edge devices through improved model orchestration and improve resource utilization based on infrastructure capabilities

### RAG
- Natural language interaction through Graph Retrieval Augmented Generation (RAG)
- Generation of insights about model relationships and performance patterns
- Interactive exploration of model metadata through graph-based queries

## Example Queries

### 1. Find models with the lowest energy consumption, output dataset name, architecture and FLOPs
```cypher
MATCH (m:Model)-[:TRAINED_ON]->(d:Dataset)
MATCH (m)-[:UTILIZES]->(a:ModelArchitecture)
MATCH (i:ModelInference)-[:INFERENCE_ON]->(m)
RETURN m.name, 
       a.type as architecture,
       d.name as dataset,
       i.energyConsumption,
       i.flops
ORDER BY i.energyConsumption ASC
```

### 2. Find models with the lowest carbon footprint
```cypher
MATCH (m:Model)-[:TRAINED_ON]->(d:Dataset)
MATCH (m)-[:UTILIZES]->(a:ModelArchitecture)
MATCH (t:ModelTraining)-[:TRAINS_ON]->(m)
WHERE d.name = "lumos5g"
RETURN m.name, t.carbonFootprint, t.mae_mean
ORDER BY t.carbonFootprint ASC
```

## License

This project is licensed under the [BSD-3 Clause License](LICENSE) - see the LICENSE file for details.

## Citation
Please cite our [paper](https://arxiv.org/abs/2505.13343) as follows:

```bibtex
@misc{mrm3,
      title={MRM3: Machine Readable ML Model Metadata}, 
      author={Andrej Čop and Blaž Bertalanič and Marko Grobelnik and Carolina Fortuna},
      year={2025},
      eprint={2505.13343},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2505.13343}, 
}
```

The example json dataset is also available on zenodo: [10.5281/zenodo.15235417](https://doi.org/10.5281/zenodo.15235417). Please cite as follows:

```bibtex
@dataset{cop_2025_15235417,
  author       = {Čop, Andrej and Bertalanic, Blaz and Fortuna, Carolina},
  title        = {MRM3: Machine Readable ML Model Metadata},
  month        = apr,
  year         = 2025,
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.15235417},
  url          = {https://doi.org/10.5281/zenodo.15235417},
}
```

## Acknowledgments

This work was supported by the Slovenian Research Agency (P20016) and the European Commission [NANCY](https://nancy-project.eu/) project (No. 101096456).

We would like to acknowledge the SensorLab team for developing the localization models, and Gregor Cerar and Tim Strnad for developing an automated training pipeline.
