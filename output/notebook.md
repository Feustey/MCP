Stratégies pour un Nœud Lightning Bitcoin Rentable
Il n'existe pas de stratégie unique et infaillible pour optimiser au mieux votre nœud Lightning afin qu'il soit rentable, car Lightning est une cible mouvante et chacun doit trouver son propre chemin [1, 2]. Cependant, l'article "Héberger un Nœud Bitcoin Lightning Rentable" partage une approche et des enseignements tirés de l'expérience d'un opérateur, qui peuvent vous éclairer [1, 2].
Il est important de noter que les nœuds Lightning les plus rentables ont souvent un avantage unique, comme une demande naturelle en tant que marchand, portefeuille mobile, échange ou fournisseur de liquidités [3, 4]. Pour un "simple pleb", certaines stratégies peuvent être envisagées [3, 4]:
•
Ouvrir de grands canaux [3, 4]. L'auteur privilégie les canaux larges, entre 5M et 25M de sats, car les grosses sorties drainent 50M à 100M [5, 6]. Si une taille devait être choisie, l'auteur suggère 5M sats [7, 8]. La taille d'un canal peut également être basée sur l'activité et la taille des canaux du nœud partenaire [5, 6].
•
Drainer de la liquidité entrante et sortante [3, 4].
•
Rechercher des scripts astucieux [3, 4].
•
Vivre une aventure et absorber des connaissances [3, 4].
Voici des éléments clés à considérer pour optimiser la rentabilité de votre nœud Lightning :
•
Gestion des frais:
◦
Définir vos frais est crucial pour gagner des sats et orienter le routage [9, 10].
◦
Vous pouvez augmenter vos frais pour diminuer le flux sortant de sats et inversement [9, 10]. Le but n'est pas toujours un canal équilibré, mais plutôt d'obtenir des sats là où ils sont les plus demandés [9, 10].
◦
L'auteur utilise une combinaison de frais dynamiques et statiques, classant ses canaux en catégories comme "Good Outbound", "Ok Outbound" et "Routeurs", avec des mises à jour de frais manuelles ou horaires basées sur le flux ou la balance [9, 10].
◦
Il est suggéré de fixer des frais plus élevés au début [11, 12]. Si un canal risque d'être drainé, alignez vos frais d'entrée sur les plus élevés du nœud partenaire, puis diminuez-les progressivement si vous ne routez pas [11, 12].
◦
Des outils comme charge-lnd peuvent être utilisés pour automatiser la définition des frais en fonction de règles et de seuils de liquidité [11, 12].
•
Liquidité:
◦
La majorité des gains de l'auteur proviennent des "puits de liquidité sortante" populaires comme LOOP, bfx-lnd0, bfx-lnd1, Nicehash et SeasickDiver [13, 14]. Il construit son nœud pour servir ces canaux en ajustant la structure des frais, la taille des canaux et le rééquilibrage [13, 14].
◦
Il est important de maintenir agressivement au moins un peu de liquidité des deux côtés de la plupart des canaux pour éviter les échecs de routage dus au manque de liquidité [15, 16].
•
Ouverture et gestion des canaux:
◦
L'approche initiale de l'auteur consistait à ouvrir un grand nombre de canaux en une seule fois [7, 8, 17, 18].
◦
Il est conseillé de ne pas créer de canaux plus petits que 2 millions de Sats [5, 6].
◦
Après avoir ouvert quelques canaux, des outils comme LNnodeinsight peuvent être utilisés pour simuler l'ouverture de canaux et identifier les améliorations potentielles [7, 8].
◦
Il est essentiel de récolter des données sur le flux de vos canaux pendant 2 à 4 semaines [18-20]. Assurez-vous que chaque canal reçoit un peu de flux entrant. Si un canal reste inactif, envisagez de le fermer [19, 20]. L'auteur a fermé 145 canaux à ce jour [19, 20].
•
Obtenir de la liquidité entrante:
◦
Plusieurs méthodes existent pour obtenir des liquidités entrantes : * Lightning Network Plus permet d'organiser des échanges de canaux [21, 22]. * Une fois établi, d'autres opérateurs peuvent être disposés à ouvrir des canaux à double financement avec vous via BOS [21, 22]. * Des fournisseurs de liquidités comme zero fee routing ou LNBig vendent de la liquidité entrante [23, 24]. L'auteur a acheté de la liquidité auprès de LNBig au début [18, 23, 24]. * Des protocoles comme LOOP ou des portefeuilles mobiles comme Wallet of Satoshi (WOS) peuvent être utilisés pour déplacer vos sats et créer de la liquidité entrante [23, 24]. * Exécuter un bon nœud encouragera d'autres à ouvrir des canaux vers vous [23, 24].
•
Rééquilibrage:
◦
Rééquilibrer signifie s'envoyer des sats à soi-même pour augmenter la liquidité entrante dans un canal et sortante dans un autre [25, 26].
◦
L'auteur rééquilibre uniquement ses canaux "Good Outbound" à un certain taux en fonction du flux actuel, car les frais doivent compenser ce coût [27, 28].
◦
Des outils en ligne de commande comme rebalance-lnd et BOS, ainsi que des interfaces graphiques comme LNDg, sont disponibles pour le rééquilibrage [27, 28].
•
Swap Out:
◦
Le "swap out" consiste à récupérer vos sats sur le réseau Bitcoin principal sans fermer vos canaux Lightning [29, 30]. Cela peut être économique pour les canaux avec des frais très élevés afin de pouvoir ouvrir de nouveaux canaux vers les nœuds "Good Outbound" après qu'ils se soient vidés [29, 30].
•
Maintenance du nœud:
◦
Plus votre nœud est actif, plus la taille de votre fichier channel.db augmentera [31, 32]. Il est nécessaire de compacter régulièrement ce fichier en redémarrant LND [31, 32].
◦
Envisagez de fermer et de rouvrir les canaux ayant un nombre élevé de mises à jour (100-200K), en vous assurant que les sats sont de votre côté du canal au préalable [33, 34].
•
Communauté:
◦
Rejoindre des communautés comme Plebnet Telegram peut être très bénéfique pour apprendre et échanger avec d'autres opérateurs de nœuds [35, 36].
En résumé, optimiser un nœud Lightning pour la rentabilité demande une compréhension approfondie des flux de liquidité, une gestion stratégique des frais, une surveillance constante des canaux et un engagement à long terme