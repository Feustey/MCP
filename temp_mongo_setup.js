// Script temporaire pour créer l'utilisateur MongoDB
db = db.getSiblingDB('admin');

// Supprimer l'ancien utilisateur s'il existe
try {
    db.dropUser('mcpuser');
    print('Ancien utilisateur supprimé');
} catch (e) {
    print('Utilisateur n\'existait pas ou erreur:', e.message);
}

// Créer le nouvel utilisateur
try {
    db.createUser({
        user: 'mcpuser',
        pwd: 'MjsKxEMsACOl_eI0cxHdpFJTGiYPJGUY',
        roles: [
            {role: 'readWrite', db: 'mcp_prod'},
            {role: 'dbAdmin', db: 'mcp_prod'},
            {role: 'readWrite', db: 'admin'}
        ]
    });
    print('✅ Utilisateur mcpuser créé avec succès');
} catch (e) {
    print('❌ Erreur lors de la création de l\'utilisateur:', e.message);
}

// Lister les utilisateurs
print('Utilisateurs existants:');
db.getUsers().forEach(function(user) {
    print('- ' + user.user + ' (' + user.roles.map(r => r.role + '@' + r.db).join(', ') + ')');
});

// Tester l'authentification
try {
    db.auth('mcpuser', 'MjsKxEMsACOl_eI0cxHdpFJTGiYPJGUY');
    print('✅ Authentification réussie');
} catch (e) {
    print('❌ Erreur d\'authentification:', e.message);
}
