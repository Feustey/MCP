# Schéma d'Architecture du Système MCP

Ce document présente un schéma visuel de l'architecture du système MCP (Monitoring and Control Platform) et de son workflow RAG.

## Vue d'ensemble de l'Architecture

```mermaid
graph TD
    subgraph "Sources de Données"
        A[Amboss Scraper] --> D[Données Brutes]
        L[LNbits] --> D
        B[Documents] --> D
    end

    subgraph "Stockage & Cache"
        D --> M[(MongoDB)]
        D --> R[(Redis Cache)]
    end

    subgraph "Moteur RAG"
        M --> EP[Embeddings Processor]
        EP --> VI[Vector Index]
        VI --> RS[Recherche Sémantique]
        RS --> CX[Contextualisation]
        CX --> LLM[OpenAI LLM]
        LLM --> RG[Réponse Générée]
        R <--> RS
        R <--> RG
    end

    subgraph "API & Services"
        RG --> AP[API]
        AP --> NR[Node Routes]
        AP --> WR[Wallet Routes]
        AP --> AR[Admin Routes]
    end

    subgraph "Sécurité & Résilience"
        CB[Circuit Breakers]
        RM[Retry Manager]
        SA[Security Audit]
        CB --- AP
        RM --- AP
        SA --- AP
    end

    subgraph "Monitoring & CI/CD"
        MT[Monitoring Tools]
        GH[GitHub Actions]
        HD[Heroku Deployment]
        MT --- AP
        GH --- HD
    end

    U[Utilisateurs] <--> AP
```

## Flux de Données RAG

```mermaid
sequenceDiagram
    participant U as Utilisateur
    participant A as API
    participant R as Redis Cache
    participant S as Système RAG
    participant M as MongoDB
    participant O as OpenAI

    U->>A: Requête utilisateur
    A->>R: Vérifier le cache
    alt Cache hit
        R->>A: Réponse en cache
        A->>U: Réponse finale
    else Cache miss
        R->>A: Pas de cache
        A->>S: Traiter la requête
        S->>M: Récupérer documents pertinents
        M->>S: Documents
        S->>O: Générer embeddings
        O->>S: Embeddings
        S->>S: Recherche sémantique
        S->>O: Générer réponse avec contexte
        O->>S: Réponse générée
        S->>R: Mettre en cache
        S->>A: Réponse
        A->>U: Réponse finale
    end
```

## Composants du Système Lightning Network

```mermaid
graph LR
    subgraph "Données Lightning"
        AS[Amboss Scraper]
        LC[LND Client]
        LB[LNbits Integration]
    end

    subgraph "Analyse et Optimisation"
        NA[Analyseur de Nœuds]
        NO[Optimiseur de Réseau]
        HA[Gestionnaire d'Hypothèses]
    end

    subgraph "API Lightning"
        NR[Routes des Nœuds]
        WR[Routes de Portefeuille]
    end

    AS --> NA
    LC --> NA
    LB --> NA
    NA --> NO
    NA --> HA
    NO --> NR
    HA --> NR
    NR --> WR
```

## Workflow CI/CD

```mermaid
graph TD
    subgraph "GitHub Actions"
        PR[Pull Request]
        PT[Tests]
        DC[Construction Docs]
        CD[Déploiement]
    end

    subgraph "Environnements"
        DV[Développement]
        ST[Staging]
        PR[Production]
    end

    subgraph "Services"
        MG[(MongoDB)]
        RD[(Redis)]
        HK[Heroku]
    end

    PR --> PT
    PT --> DC
    DC --> CD
    CD --> DV
    DV --> ST
    ST --> PR
    PR --> HK
    HK --> MG
    HK --> RD
```

## Légende

- **Sources de Données**: Origines des données traitées par le système
- **Stockage & Cache**: Systèmes de persistance et mise en cache
- **Moteur RAG**: Composants du système de Retrieval-Augmented Generation
- **API & Services**: Points d'entrée pour les utilisateurs
- **Sécurité & Résilience**: Fonctionnalités assurant la robustesse du système
- **Monitoring & CI/CD**: Outils de surveillance et déploiement continu 