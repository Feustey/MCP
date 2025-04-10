import asyncio
from mongo_operations import MongoOperations
from trainer import Trainer
from src.ml.evaluation.evaluator import ModelEvaluator
from src.ml.evaluation.metrics_storage import MetricsStorage
from src.ml.evaluation.visualization import MetricsVisualizer

async def check_recommendations():
    mongo_ops = MongoOperations()
    node_id = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
    
    recommendations = await mongo_ops.get_node_recommendations(node_id)
    print(f"\nRecommandations trouvées pour le nœud {node_id}:")
    for rec in recommendations:
        print("\nRecommandation:")
        print(f"Contenu: {rec.content}")
        print(f"Date de création: {rec.created_at}")
        print(f"Score de confiance: {rec.confidence_score}")
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(check_recommendations())

trainer = Trainer(
    model=model,
    optimizer=optimizer,
    loss_fn=loss_fn,
    metrics=["accuracy", "precision", "recall", "f1"],
    redis_config={
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "prefix": "metrics:"
    }
)

# Initialisation
evaluator = ModelEvaluator(n_splits=5)
storage = MetricsStorage("mongodb://localhost:27017")
visualizer = MetricsVisualizer()

# Évaluation
results = evaluator.cross_validate(model, X, y)

# Sauvegarde des résultats
storage.save_metrics("run_1", "1.0.0", results, model.get_params())

# Visualisation
visualizer.plot_learning_curves(train_scores, val_scores, "accuracy")
visualizer.plot_confusion_matrix(results['confusion_matrix']) 