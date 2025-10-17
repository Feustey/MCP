---
name: 🚀 Deployment Issue
about: Report a problem with CI/CD deployment
title: '[DEPLOY] '
labels: deployment, bug
assignees: ''
---

## 🚀 Deployment Information

**Workflow Run ID:** [Link to GitHub Actions run]
**Branch:** [e.g., main]
**Commit SHA:** [e.g., a1b2c3d]
**Deployment Time:** [e.g., 2025-10-17 14:30:00 UTC]

## 📝 Description

A clear and concise description of what went wrong during deployment.

## 🔍 Steps to Reproduce

1. Go to '...'
2. Click on '....'
3. See error

## 🐛 Expected Behavior

What should have happened during the deployment.

## 🔴 Actual Behavior

What actually happened.

## 📊 Logs

```bash
# Paste relevant logs from GitHub Actions or server
```

## 🖥️ Server Status

```bash
# Output of: docker-compose ps
```

## 🏥 Health Check

```bash
# Output of: curl https://api.dazno.de/api/v1/health
```

## 🔄 Rollback Status

- [ ] Rollback was attempted
- [ ] Rollback was successful
- [ ] Service is currently healthy
- [ ] Previous version restored

## 📱 Additional Context

Add any other context about the problem here.

## ✅ Checklist

- [ ] I checked the GitHub Actions logs
- [ ] I checked the server logs (`docker-compose logs`)
- [ ] I verified the health endpoint
- [ ] I checked the backups are available
- [ ] I tried to rollback manually

