import numpy as np
from sklearn.datasets import make_classification
from sklearn.preprocessing import StandardScaler
from src.ml import NeuralNetwork, Adam, MSE, Trainer

def main():
    # Génération de données synthétiques
    X, y = make_classification(
        n_samples=1000,
        n_features=20,
        n_informative=15,
        n_redundant=5,
        random_state=42
    )
    
    # Normalisation des données
    scaler = StandardScaler()
    X = scaler.fit_transform(X)
    y = y.reshape(-1, 1)
    
    # Création du modèle
    model = NeuralNetwork(
        input_size=20,
        hidden_sizes=[64, 32],
        output_size=1
    )
    
    # Initialisation de l'optimiseur
    optimizer = Adam(
        parameters=model.parameters,
        learning_rate=0.001
    )
    
    # Initialisation de la fonction de perte
    loss_fn = MSE()
    
    # Configuration de l'entraînement
    trainer = Trainer(
        model=model,
        optimizer=optimizer,
        loss_fn=loss_fn,
        batch_size=32,
        num_epochs=100,
        validation_split=0.2,
        early_stopping_patience=5
    )
    
    # Entraînement du modèle
    metrics = trainer.train(X, y)
    
    # Affichage des résultats
    print("\nRésultats de l'entraînement:")
    print(f"Meilleure perte de validation: {min(metrics['loss']):.4f}")
    print(f"Temps moyen par époque: {np.mean(metrics['epoch_time']):.2f}s")

if __name__ == "__main__":
    main() 