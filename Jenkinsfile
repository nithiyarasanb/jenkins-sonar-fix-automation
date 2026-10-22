pipeline {
    agent { label 'linux-python-git' }

    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        PYTHONUNBUFFERED = '1'
        REMEDIATION_RESULTS = 'remediation-results'
        // Set these as Jenkins job/folder environment variables:
        // SONAR_HOST_URL, SONAR_PROJECT_KEY, BITBUCKET_BASE_URL,
        // BITBUCKET_WORKSPACE, BITBUCKET_REPO_SLUG, BITBUCKET_DEFAULT_BRANCH.
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git status --short'
            }
        }

        // Reuse your existing build/test/Sonar stages here.
        // This starter assumes the SonarQube analysis for this revision is complete.
        stage('Collect Critical/High Findings') {
            steps {
                withCredentials([string(credentialsId: 'sonarqube-token', variable: 'SONAR_TOKEN')]) {
                    sh 'python3 remediation/collect_findings.py'
                }
            }
        }

        stage('Generate Proposed Fixes') {
            when {
                expression { fileExists('remediation-results/findings.json') }
            }
            steps {
                script {
                    if (env.REMEDIATION_MODE in ['ai', 'hybrid']) {
                        withCredentials([string(credentialsId: 'remediation-ai-token', variable: 'AI_API_KEY')]) {
                            sh 'python3 remediation/propose_fixes.py'
                        }
                    } else {
                        sh 'python3 remediation/propose_fixes.py'
                    }
                }
            }
        }

        stage('Validate Proposed Fixes') {
            steps {
                // Set VALIDATION_COMMAND to a trusted, repository-specific test command.
                // Do not interpolate user-controlled input into shell commands.
                sh 'python3 remediation/validate_patch.py'
            }
        }

        stage('Publish Remediation Branch') {
            when {
                expression { return fileExists('remediation-results/validated.patch') }
            }
            steps {
                script {
                    if (!env.REMEDIATION_BRANCH?.startsWith('sonar-remediation/')) {
                        error('Set REMEDIATION_BRANCH to a unique sonar-remediation/<id> branch name')
                    }
                }
                sh 'python3 remediation/publish_branch.py'
                // Configure this SSH credential with write access only to the target repo.
                sshagent(credentials: ['bitbucket-ssh-key']) {
                    sh 'git push origin "$REMEDIATION_BRANCH"'
                }
            }
        }

        stage('Create Bitbucket Pull Request') {
            when {
                expression { return fileExists('remediation-results/validated.patch') }
            }
            steps {
                withCredentials([string(credentialsId: 'bitbucket-token', variable: 'BITBUCKET_TOKEN')]) {
                    sh 'python3 remediation/create_pr.py'
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'remediation-results/**', allowEmptyArchive: true
            cleanWs(deleteDirs: true, notFailBuild: true)
        }
    }
}
