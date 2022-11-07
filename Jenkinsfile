pipeline {
    agent {
        docker {
            image 'danischm/aac:0.4.2'
            label 'emear-sio-slv01 || emear-sio-slv02 || emear-sio-slv03 || emear-sio-slv04 || emear-sio-slv05'
            args '-u root'
        }
    }

    parameters {
        booleanParam(name: 'APIC_SNAPSHOT', defaultValue: true, description: 'Enable APIC snapshot before deployment')
        booleanParam(name: 'APIC_DEPLOY', defaultValue: true, description: 'Enable APIC deploy stage')
        booleanParam(name: 'FULL_APIC_DEPLOY', defaultValue: false, description: 'Full APIC deploy')
        booleanParam(name: 'TEST_APIC_DEPLOY', defaultValue: true, description: 'Enable APIC test deploy stage')
        booleanParam(name: 'FULL_APIC_TEST', defaultValue: false, description: 'Full APIC test')
        booleanParam(name: 'MSO_DEPLOY', defaultValue: true, description: 'Enable MSO deploy stage')
        booleanParam(name: 'FULL_MSO_DEPLOY', defaultValue: false, description: 'Full MSO deploy')
        booleanParam(name: 'TEST_MSO_DEPLOY', defaultValue: true, description: 'Enable MSO test deploy stage')
        booleanParam(name: 'FULL_MSO_TEST', defaultValue: false, description: 'Full MSO test')
        booleanParam(name: 'NAE_PCV', defaultValue: false, description: 'Enable NAE Pre-Change Validation')
    }

    environment { 
        ANSIBLE_VAULT_PASSWORD = credentials('ANSIBLE_VAULT_PASSWORD')
        APIC_HOST = credentials('APIC_HOST')
        MSO_HOST = credentials('MSO_HOST')
        WEBEX_TOKEN = credentials('WEBEX_TOKEN')
        WEBEX_ROOM_ID = "Y2lzY29zcGFyazovL3VzL1JPT00vNTFmMGNmODAtYjI0My0xMWU5LTljZjUtNWY0NGQ2ZTlmYWY0"
        GITHUB_TOKEN = credentials('GITHUB_TOKEN')
        CONFIG_REPO_OWNER = "netascode"
        CONFIG_REPO_NAME = "aac-config"
        REPO = env.GIT_URL.replaceFirst(/^.*?(?::\/\/.*?\/|:)(.*).git$/, '$1')
        GIT_COMMIT_MESSAGE = "${sh(returnStdout: true, script: 'git config --global --add safe.directory "*" && git log -1 --pretty=%B ${GIT_COMMIT}').trim()}"
        GIT_COMMIT_AUTHOR = "${sh(returnStdout: true, script: 'git show -s --pretty=%an').trim()}"
        GIT_COMMIT_EMAIL = "${sh(returnStdout: true, script: 'git show -s --pretty=%ae').trim()}"
        GIT_EVENT = "${(env.CHANGE_ID != null) ? 'Pull Request' : 'Push'}"
    }

    options {
        disableConcurrentBuilds()
    }

    stages {
        stage('Setup') {
            steps {
                sh 'ansible-galaxy install -r requirements.yml'
                sh 'mkdir previous && git clone --depth 1 --branch last_deploy https://wwwin-github.cisco.com/${REPO}.git previous/'
                sh 'git clone https://wwwin-github.cisco.com/${CONFIG_REPO_OWNER}/${CONFIG_REPO_NAME}.git'
            }
        }
        stage('Validate') {
            steps {
                sh 'set -o pipefail && ansible-playbook -i data/lab/hosts.yaml apic_validate.yaml |& tee validate_output.txt'
                sh 'set -o pipefail && ansible-playbook -i data/lab/hosts.yaml mso_validate.yaml |& tee validate_output.txt'
            }
        }
        stage('Render APIC') {
            steps {
                sh "echo 'previous_inventory: \"./previous/data/lab/\"' >> apic_render_vars.yaml"
                sh '''
                    if [ "${FULL_APIC_DEPLOY}" == "true" ]; then
                        echo "apic_mode: 'all'" >> apic_render_vars.yaml
                    fi
                '''
                sh 'set -o pipefail && ANSIBLE_CONFIG=$(pwd)/ansible.cfg ansible-playbook -i data/lab/hosts.yaml -e @apic_render_vars.yaml apic_render.yaml |& tee render_output.txt'
                sh '''
                    if [ -d "./rendered" ]; then
                        /bin/cp -rf ./rendered/ "./${CONFIG_REPO_NAME}/"
                    fi
                '''
            }
        }
        stage('NAE Pre-Change Validation') {
            when {
                changeRequest target: 'master'
                expression { return params.NAE_PCV }
            }
            environment {
                NAE_HOST = credentials('NAE_HOST')
                NAE_PASSWORD = credentials('NAE_PASSWORD')
            }
            steps {
                sh "echo 'apic_nae_pca: ${params.NAE_PCV}' >> apic_nae_vars.yaml"
                sh "echo 'nae_pca_name: \"Jenkins Build ${BUILD_DISPLAY_NAME} PR #${BUILD_DISPLAY_NAME}\"' >> apic_nae_vars.yaml"
                sh 'set -o pipefail && ANSIBLE_CONFIG=$(pwd)/ansible.cfg ansible-playbook -i data/lab/hosts.yaml -e @apic_nae_vars.yaml apic_nae_pca.yaml |& tee nae_output.txt'
            }
        }
        stage('Deploy APIC') {
            when {
                branch "master"
            }
            steps {
                sh "echo 'apic_snapshot: ${params.APIC_SNAPSHOT}' >> apic_deploy_vars.yaml"
                sh "echo 'apic_deploy: ${params.APIC_DEPLOY}' >> apic_deploy_vars.yaml"
                sh "echo 'previous_inventory: \"./previous/data/lab/\"' >> apic_deploy_vars.yaml"
                sh '''
                    if [ "${FULL_APIC_DEPLOY}" == "true" ]; then
                        echo "apic_mode: 'all'" >> apic_deploy_vars.yaml
                    fi
                '''
                sh 'set -o pipefail && ANSIBLE_CONFIG=$(pwd)/ansible.cfg ansible-playbook -i data/lab/hosts.yaml -e @apic_deploy_vars.yaml apic_deploy.yaml |& tee deploy_output.txt'
            }
        }
        stage('Deploy MSO') {
            when {
                branch "master"
            }
            steps {
                sh "echo 'mso_deploy: ${params.MSO_DEPLOY}' >> mso_deploy_vars.yaml"
                sh "echo 'previous_inventory: \"./previous/data/lab/\"' >> mso_deploy_vars.yaml"
                sh '''
                    if [ "${FULL_MSO_DEPLOY}" == "true" ]; then
                        echo "mso_mode: 'all'" >> mso_deploy_vars.yaml
                    fi
                '''
                sh 'set -o pipefail && ANSIBLE_CONFIG=$(pwd)/ansible.cfg ansible-playbook -i data/lab/hosts.yaml -e @mso_deploy_vars.yaml mso_deploy.yaml |& tee deploy_output.txt'
            }
        }
        stage('Test') {
            when {
                branch "master"
            }
            parallel {
                stage('Test APIC') {
                    steps {
                        sh "echo 'test_apic_deploy: ${params.TEST_APIC_DEPLOY}' >> apic_test_vars.yaml"
                        sh "echo 'previous_inventory: \"./previous/data/lab/\"' >> apic_test_vars.yaml"
                        sh '''
                            if [ "${FULL_APIC_TEST}" == "true" ]; then
                                echo "apic_mode: 'all'" >> apic_test_vars.yaml
                            fi
                        '''
                        sh 'set -o pipefail && ANSIBLE_CONFIG=$(pwd)/ansible.cfg ansible-playbook -i data/lab/hosts.yaml -e @apic_test_vars.yaml apic_test.yaml |& tee test_output.txt'
                    }
                    post {
                        always {
                            junit testResults: 'test_results/lab/apic1/xunit.xml', allowEmptyResults: true
                            archiveArtifacts artifacts: 'test_results/lab/apic1/*.html, test_results/lab/apic1/*.xml', allowEmptyArchive: true
                        }
                    }
                }
                stage('Test MSO') {
                    steps {
                        sh "echo 'test_mso_deploy: ${params.TEST_MSO_DEPLOY}' >> mso_test_vars.yaml"
                        sh "echo 'previous_inventory: \"./previous/data/lab/\"' >> mso_test_vars.yaml"
                        sh '''
                            if [ "${FULL_MSO_TEST}" == "true" ]; then
                                echo "mso_mode: 'all'" >> mso_test_vars.yaml
                            fi
                        '''
                        sh 'set -o pipefail && ANSIBLE_CONFIG=$(pwd)/ansible.cfg ansible-playbook -i data/lab/hosts.yaml -e @mso_test_vars.yaml mso_test.yaml |& tee test_output.txt'
                    }
                    post {
                        always {
                            junit testResults: 'test_results/lab/mso1/xunit.xml', allowEmptyResults: true
                            archiveArtifacts artifacts: 'test_results/lab/mso1/*.html, test_results/lab/mso1/*.xml', allowEmptyArchive: true
                        }
                    }
                }
            }
        }
        stage('Git Updates') {
            when {
                branch "master"
            }
            steps {
                sh '''
                    cd "${CONFIG_REPO_NAME}"
                    git config credential.helper "store --file=.git/credentials"
                    echo "https://${GITHUB_TOKEN}:@wwwin-github.cisco.com" > .git/credentials
                    git config user.email "${GIT_COMMIT_AUTHOR}"
                    git config user.name "${GIT_COMMIT_EMAIL}"
                    git add -A
                    git commit -a -m "${GIT_COMMIT_MESSAGE}" --allow-empty
                    git push
                '''
                sh '''
                    git config credential.helper "store --file=.git/credentials"
                    echo "https://${GITHUB_TOKEN}:@wwwin-github.cisco.com" > .git/credentials
                    git tag -d last_deploy
                    git push --delete origin last_deploy
                    git tag last_deploy
                    git push --tags
                '''
            }
        }
    }
    
    post {
        always {
            sh "BUILD_STATUS=${currentBuild.currentResult} python3 .ci/webex-notification-jenkins.py"
            sh 'rm -rf *.txt *.yaml previous ${CONFIG_REPO_NAME} test_results rendered'
        }
    }
}